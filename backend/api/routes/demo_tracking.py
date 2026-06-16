"""
Routes API — tracking des vues démos.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from db.demo_tracking_store import get_demo_tracking_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demo-tracking"])


class RecordDemoViewBody(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=128)
    demo_url: str = Field(..., min_length=1, max_length=2048)


def _client_ip(request: Request) -> str | None:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    client = request.client
    if client and client.host:
        return str(client.host)
    return None


def _tracking_error(exc: SupabaseStoreError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/demo-tracking/view")
async def record_demo_view(body: RecordDemoViewBody, request: Request) -> dict:
    """Enregistre une vue démo (endpoint public, sans auth)."""
    store = get_demo_tracking_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.record_view(
            body.project_id,
            body.demo_url,
            visitor_ip=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            referer=request.headers.get("Referer"),
        )
    except SupabaseStoreError as exc:
        raise _tracking_error(exc) from exc
    return {"recorded": True, "id": row.get("id"), "device_type": row.get("device_type")}


@router.get("/demo-tracking/{project_id}/stats")
async def get_demo_tracking_stats(project_id: str) -> dict:
    store = get_demo_tracking_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    return await store.get_stats(project_id)


@router.get("/demo-tracking/{project_id}/views")
async def list_demo_tracking_views(project_id: str) -> dict:
    store = get_demo_tracking_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    items = await store.list_views(project_id)
    return {"items": items, "count": len(items)}
