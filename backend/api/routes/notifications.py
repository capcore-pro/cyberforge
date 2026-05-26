"""
Notifications CyberForge — contacts démo non lus (badge Clients + toast).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.demos_store import DemoContactNotification, SupabaseStoreError, get_demos_store

router = APIRouter(tags=["notifications"])


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


def _to_item(row: DemoContactNotification) -> ContactNotificationItem:
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
    items = [_to_item(r) for r in rows]
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
