"""
Routes API — Audit logs (Volume 3).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from db.audit_store import get_audit_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audit"])


@router.get("/audit/events")
async def list_audit_events(
    event_type: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    store = get_audit_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_events(
            event_type=event_type,
            project_id=project_id,
            limit=limit,
        )
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_audit_events: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
