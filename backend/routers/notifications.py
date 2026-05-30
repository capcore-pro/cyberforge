"""
Notifications système CyberForge — persistance Supabase, SSE temps réel, Telegram.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings, plain_secret_str
from cache import ttl_cache
from db.supabase_store import SupabaseStoreError, _raise_for_status, _raise_transport_error, get_supabase_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

KEEPALIVE_SECONDS = 30
TELEGRAM_LEVELS = frozenset({"error", "warning"})


class NotificationRow(BaseModel):
    id: str
    type: str
    level: str
    title: str
    message: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    read: bool = False
    telegram_sent: bool = False
    created_at: str


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1)
    type: str = Field(min_length=1)
    level: str = "info"
    message: str | None = None
    project_id: str | None = None
    project_name: str | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationRow]


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int


class ClearResponse(BaseModel):
    deleted: int


class NotificationBroadcaster:
    """Fan-out SSE en mémoire (process local)."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any] | None]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any] | None]:
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            await queue.put(payload)


_broadcaster = NotificationBroadcaster()


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    status = 502
    if detail.get("status_code") == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


def _require_store():
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    return store


def _row_from_dict(data: dict[str, Any]) -> NotificationRow:
    return NotificationRow(
        id=str(data["id"]),
        type=str(data.get("type") or ""),
        level=str(data.get("level") or "info"),
        title=str(data.get("title") or ""),
        message=data.get("message") if isinstance(data.get("message"), str) else None,
        project_id=data.get("project_id") if isinstance(data.get("project_id"), str) else None,
        project_name=data.get("project_name") if isinstance(data.get("project_name"), str) else None,
        read=bool(data.get("read")),
        telegram_sent=bool(data.get("telegram_sent")),
        created_at=str(data.get("created_at") or ""),
    )


def _insert_payload(
    *,
    title: str,
    type: str,
    level: str,
    message: str | None,
    project_id: str | None,
    project_name: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": type,
        "level": level,
        "title": title,
    }
    if message is not None:
        payload["message"] = message
    if project_id is not None:
        payload["project_id"] = project_id
    if project_name is not None:
        payload["project_name"] = project_name
    return payload


async def send_telegram(
    *,
    title: str,
    level: str,
    message: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> bool:
    """Envoie sur Telegram uniquement pour level error ou warning."""
    if level not in TELEGRAM_LEVELS:
        return False

    settings = get_settings()
    token = plain_secret_str(settings.telegram_bot_token)
    chat_id = (settings.telegram_chat_id or "").strip()
    if not token or not chat_id:
        logger.warning("Telegram non configuré — notification %s non envoyée", level)
        return False

    icon = "🚨" if level == "error" else "⚠️"
    lines = [f"{icon} [{level.upper()}] {title.strip()}"]
    if message and message.strip():
        lines.append(message.strip())
    if project_name or project_id:
        project_line = project_name.strip() if project_name else ""
        if project_id:
            project_line = f"{project_line} ({project_id})" if project_line else project_id
        lines.append(f"Projet : {project_line}")

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        if resp.status_code >= 400:
            logger.warning(
                "Telegram HTTP %s — %s",
                resp.status_code,
                resp.text.strip()[:300],
            )
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("Telegram indisponible : %s", exc)
        return False


async def _mark_telegram_sent(store, notification_id: str) -> None:
    url = f"{store._rest_url()}/notifications"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.patch(
                url,
                headers=store._headers(),
                params={"id": f"eq.{notification_id}"},
                json={"telegram_sent": True},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "mark_telegram_sent", "PATCH", url, store)
        _raise_for_status(resp, "mark_telegram_sent", "PATCH", url, store)


async def notify(
    title: str,
    type: str,
    level: str = "info",
    message: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> NotificationRow:
    """Insère une notification en Supabase, envoie Telegram si besoin, broadcast SSE."""
    store = get_supabase_store()
    if not store.is_configured():
        raise SupabaseStoreError("Supabase non configuré.")
    url = f"{store._rest_url()}/notifications"
    payload = _insert_payload(
        title=title,
        type=type,
        level=level,
        message=message,
        project_id=project_id,
        project_name=project_name,
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                url,
                headers=store._headers("return=representation"),
                json=payload,
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "notify", "POST", url, store)
        _raise_for_status(resp, "notify", "POST", url, store)

    data = resp.json()
    if not isinstance(data, list) or not data:
        raise SupabaseStoreError("Insertion notification sans identifiant retourné.")
    row = _row_from_dict(data[0])

    if level in TELEGRAM_LEVELS:
        sent = await send_telegram(
            title=title,
            level=level,
            message=message,
            project_id=project_id,
            project_name=project_name,
        )
        if sent:
            await _mark_telegram_sent(store, row.id)
            row = row.model_copy(update={"telegram_sent": True})

    await _broadcaster.broadcast({"type": "notification", "data": row.model_dump(mode="json")})
    return row


def schedule_notify(
    title: str,
    type: str,
    level: str = "info",
    message: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> None:
    """Planifie notify() depuis un contexte sync ou thread (fire-and-forget)."""

    async def _run() -> None:
        try:
            await notify(title, type, level, message, project_id, project_name)
        except Exception as exc:
            logger.warning("Notification ignorée (%s): %s", type, exc)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        try:
            asyncio.run(_run())
        except Exception as exc:
            logger.warning("Notification ignorée (%s): %s", type, exc)


@router.get("/notifications/stream")
async def notifications_stream() -> StreamingResponse:
    """SSE — nouvelles notifications en temps réel (keepalive 30 s)."""

    async def event_generator() -> AsyncIterator[str]:
        queue = await _broadcaster.subscribe()
        try:
            yield _sse_line({"type": "stream_start"})
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield _sse_line({"type": "keepalive"})
                    continue
                if item is None:
                    break
                yield _sse_line(item)
        finally:
            await _broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
@ttl_cache(seconds=30.0)
async def notifications_unread_count() -> UnreadCountResponse:
    store = _require_store()
    url = f"{store._rest_url()}/notifications"
    headers = {**store._headers(), "Prefer": "count=exact"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                url,
                headers=headers,
                params={"select": "id", "read": "eq.false"},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "unread_count", "GET", url, store)
        _raise_for_status(resp, "unread_count", "GET", url, store)

    count = 0
    content_range = resp.headers.get("content-range", "")
    if "/" in content_range:
        try:
            count = int(content_range.split("/")[-1])
        except ValueError:
            count = 0
    return UnreadCountResponse(count=count)


@router.patch("/notifications/read-all", response_model=MarkAllReadResponse)
async def notifications_mark_all_read() -> MarkAllReadResponse:
    store = _require_store()
    url = f"{store._rest_url()}/notifications"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.patch(
                url,
                headers=store._headers("return=representation"),
                params={"read": "eq.false"},
                json={"read": True},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "read_all", "PATCH", url, store)
        _raise_for_status(resp, "read_all", "PATCH", url, store)

    rows = resp.json()
    marked = len(rows) if isinstance(rows, list) else 0
    return MarkAllReadResponse(marked=marked)


@router.delete("/notifications/clear", response_model=ClearResponse)
async def notifications_clear() -> ClearResponse:
    store = _require_store()
    url = f"{store._rest_url()}/notifications"
    count_headers = {**store._headers(), "Prefer": "count=exact"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            count_resp = await client.head(
                url,
                headers=count_headers,
                params={"select": "id"},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "clear_count", "HEAD", url, store)
        _raise_for_status(count_resp, "clear_count", "HEAD", url, store)

        deleted = 0
        content_range = count_resp.headers.get("content-range", "")
        if "/" in content_range:
            try:
                deleted = int(content_range.split("/")[-1])
            except ValueError:
                deleted = 0

        try:
            delete_resp = await client.delete(
                url,
                headers=store._headers("return=minimal"),
                params={"id": "not.is.null"},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "clear", "DELETE", url, store)
        _raise_for_status(delete_resp, "clear", "DELETE", url, store)

    return ClearResponse(deleted=deleted)


@router.get("/notifications/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    store = _require_store()
    url = f"{store._rest_url()}/notifications"
    params: dict[str, str] = {
        "select": "*",
        "order": "created_at.desc",
        "limit": "50",
    }
    if unread_only:
        params["read"] = "eq.false"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=store._headers(), params=params)
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "list_notifications", "GET", url, store)
        _raise_for_status(resp, "list_notifications", "GET", url, store)

    rows = resp.json()
    items = [_row_from_dict(row) for row in rows] if isinstance(rows, list) else []
    return NotificationListResponse(items=items)


@router.post("/notifications/", response_model=NotificationRow, status_code=201)
async def create_notification(body: NotificationCreate) -> NotificationRow:
    try:
        return await notify(
            body.title,
            body.type,
            body.level,
            body.message,
            body.project_id,
            body.project_name,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /notifications/") from exc


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRow)
async def mark_notification_read(notification_id: str) -> NotificationRow:
    store = _require_store()
    url = f"{store._rest_url()}/notifications"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.patch(
                url,
                headers=store._headers("return=representation"),
                params={"id": f"eq.{notification_id}"},
                json={"read": True},
            )
        except httpx.HTTPError as exc:
            _raise_transport_error(exc, "mark_read", "PATCH", url, store)
        _raise_for_status(resp, "mark_read", "PATCH", url, store)

    rows = resp.json()
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail={"message": "Notification introuvable."})
    return _row_from_dict(rows[0])
