"""
Notifications CyberForge — système (mémoire) + contacts démo (Supabase).
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.notifications_memory import (
    ClearResponse,
    MarkAllReadResponse,
    NotificationCreate,
    NotificationListResponse,
    NotificationRow,
    UnreadCountResponse,
    get_notification_store,
    notify,
)
from db.demos_store import DemoContactNotification, SupabaseStoreError, get_demos_store

router = APIRouter(tags=["notifications"])

_notif_cache: UnreadCountResponse | None = None
_notif_cache_time = 0.0
NOTIF_CACHE_TTL = 30  # secondes


def _invalidate_notif_cache() -> None:
    global _notif_cache
    _notif_cache = None


# --- Contacts démo (Supabase) -------------------------------------------------


class ContactNotificationItem(BaseModel):
    demo_id: str
    token: str
    title: str
    interested_at: str
    client_name: str | None = None
    client_email: str | None = None


class ContactNotificationsResponse(BaseModel):
    unread_count: int
    items: list[ContactNotificationItem]


class MarkContactNotificationsSeenResponse(BaseModel):
    marked: int


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    status = 502
    if detail.get("status_code") == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


def _to_contact_item(row: DemoContactNotification) -> ContactNotificationItem:
    contact = row.interest_contact or {}
    return ContactNotificationItem(
        demo_id=row.id,
        token=row.token,
        title=row.title,
        interested_at=row.interested_at or "",
        client_name=contact.get("name") if isinstance(contact.get("name"), str) else None,
        client_email=contact.get("email") if isinstance(contact.get("email"), str) else None,
    )


@router.get("/notifications/contacts", response_model=ContactNotificationsResponse)
async def list_contact_notifications() -> ContactNotificationsResponse:
    """Contacts démo non lus (statut intéressée, pas encore vus dans CyberForge)."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        rows = await store.list_unread_contact_notifications()
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /notifications/contacts") from exc
    items = [_to_contact_item(r) for r in rows]
    return ContactNotificationsResponse(unread_count=len(items), items=items)


@router.get("/notifications/contacts/unread-count")
async def contact_notifications_unread_count() -> dict[str, int]:
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        count = await store.count_unread_contact_notifications()
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /notifications/contacts/unread-count") from exc
    return {"unread_count": count}


@router.post(
    "/notifications/contacts/mark-seen",
    response_model=MarkContactNotificationsSeenResponse,
)
async def mark_contact_notifications_seen() -> MarkContactNotificationsSeenResponse:
    """Marque tous les contacts démo comme vus (badge disparaît)."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        marked = await store.mark_contact_notifications_seen()
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /notifications/contacts/mark-seen") from exc
    return MarkContactNotificationsSeenResponse(marked=marked)


# --- Notifications système (mémoire) ------------------------------------------


def _not_found(notification_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"message": "Notification introuvable.", "id": notification_id},
    )


@router.get("/notifications", response_model=NotificationListResponse)
@router.get("/notifications/", response_model=NotificationListResponse, include_in_schema=False)
async def list_notifications(
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    """Liste des notifications système (stockage en mémoire)."""
    items = await get_notification_store().list_items(unread_only=unread_only)
    return NotificationListResponse(items=items)


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def notifications_unread_count() -> UnreadCountResponse:
    global _notif_cache, _notif_cache_time

    now = time.time()
    if _notif_cache is not None and (now - _notif_cache_time) < NOTIF_CACHE_TTL:
        return _notif_cache

    count = await get_notification_store().unread_count()
    result = UnreadCountResponse(count=count)

    _notif_cache = result
    _notif_cache_time = now
    return result


@router.post("/notifications", response_model=NotificationRow, status_code=201)
@router.post("/notifications/", response_model=NotificationRow, status_code=201, include_in_schema=False)
async def create_notification(body: NotificationCreate) -> NotificationRow:
    """Crée une notification système (test / intégrations internes)."""
    row = await notify(
        body.title,
        body.type,
        body.level,
        message=body.message,
        project_id=body.project_id,
        project_name=body.project_name,
    )
    _invalidate_notif_cache()
    return row


async def _mark_read_handler(notification_id: str) -> NotificationRow:
    row = await get_notification_store().mark_read(notification_id)
    if row is None:
        raise _not_found(notification_id)
    _invalidate_notif_cache()
    return row


@router.post("/notifications/mark-read/{notification_id}", response_model=NotificationRow)
async def mark_notification_read_post(notification_id: str) -> NotificationRow:
    """Marque une notification comme lue."""
    return await _mark_read_handler(notification_id)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRow)
async def mark_notification_read_patch(notification_id: str) -> NotificationRow:
    """Alias PATCH — compatibilité frontend existant."""
    return await _mark_read_handler(notification_id)


async def _mark_all_read_handler() -> MarkAllReadResponse:
    marked = await get_notification_store().mark_all_read()
    _invalidate_notif_cache()
    return MarkAllReadResponse(marked=marked)


@router.post("/notifications/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_notifications_read_post() -> MarkAllReadResponse:
    """Marque toutes les notifications comme lues."""
    return await _mark_all_read_handler()


@router.patch("/notifications/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read_patch() -> MarkAllReadResponse:
    """Alias PATCH — compatibilité frontend existant."""
    return await _mark_all_read_handler()


@router.delete("/notifications/clear", response_model=ClearResponse)
async def clear_notifications() -> ClearResponse:
    """Supprime tout l'historique en mémoire."""
    deleted = await get_notification_store().clear()
    _invalidate_notif_cache()
    return ClearResponse(deleted=deleted)
