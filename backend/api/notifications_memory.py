"""
Notifications système — stockage en mémoire (process local).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_NOTIFICATIONS = 200
VALID_LEVELS = frozenset({"info", "success", "warning", "error"})


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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_level(level: str) -> str:
    cleaned = (level or "info").strip().lower()
    return cleaned if cleaned in VALID_LEVELS else "info"


class NotificationMemoryStore:
    """File d'attente de notifications en RAM (non persistée)."""

    def __init__(self) -> None:
        self._items: list[NotificationRow] = []
        self._lock = asyncio.Lock()

    async def list_items(self, *, unread_only: bool = False) -> list[NotificationRow]:
        async with self._lock:
            rows = list(self._items)
        if unread_only:
            rows = [row for row in rows if not row.read]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows[:50]

    async def unread_count(self) -> int:
        async with self._lock:
            return sum(1 for row in self._items if not row.read)

    async def add(
        self,
        *,
        title: str,
        type: str,
        level: str = "info",
        message: str | None = None,
        project_id: str | None = None,
        project_name: str | None = None,
    ) -> NotificationRow:
        row = NotificationRow(
            id=str(uuid4()),
            type=(type or "system").strip(),
            level=_normalize_level(level),
            title=title.strip(),
            message=(message or "").strip() or None,
            project_id=(project_id or "").strip() or None,
            project_name=(project_name or "").strip() or None,
            read=False,
            telegram_sent=False,
            created_at=_now_iso(),
        )
        async with self._lock:
            self._items.insert(0, row)
            if len(self._items) > MAX_NOTIFICATIONS:
                self._items = self._items[:MAX_NOTIFICATIONS]
        return row

    async def mark_read(self, notification_id: str) -> NotificationRow | None:
        async with self._lock:
            for index, row in enumerate(self._items):
                if row.id != notification_id:
                    continue
                updated = row.model_copy(update={"read": True})
                self._items[index] = updated
                return updated
        return None

    async def mark_all_read(self) -> int:
        marked = 0
        async with self._lock:
            next_items: list[NotificationRow] = []
            for row in self._items:
                if row.read:
                    next_items.append(row)
                    continue
                next_items.append(row.model_copy(update={"read": True}))
                marked += 1
            self._items = next_items
        return marked

    async def clear(self) -> int:
        async with self._lock:
            deleted = len(self._items)
            self._items.clear()
        return deleted


_store = NotificationMemoryStore()


def get_notification_store() -> NotificationMemoryStore:
    return _store


async def notify(
    title: str,
    type: str,
    level: str = "info",
    message: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> NotificationRow:
    """Crée une notification en mémoire (utilisable depuis le pipeline / agents)."""
    return await _store.add(
        title=title,
        type=type,
        level=level,
        message=message,
        project_id=project_id,
        project_name=project_name,
    )


def schedule_notify(
    title: str,
    type: str,
    level: str = "info",
    message: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> None:
    """Planifie notify() depuis un contexte sync (fire-and-forget)."""

    async def _run() -> None:
        try:
            await notify(
                title,
                type,
                level,
                message=message,
                project_id=project_id,
                project_name=project_name,
            )
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
