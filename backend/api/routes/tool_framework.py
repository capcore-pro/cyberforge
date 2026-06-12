"""
Routes API — Tool Framework (registre, stats, disponibilité).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from db.supabase_store import SupabaseStoreError
from db.tool_store import get_tool_store
from tools.wrappers import is_tool_available

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tool_framework"])


@router.get("/tools")
async def list_tools() -> dict:
    store = get_tool_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_tools()
        enriched = [
            {**row, "is_available": is_tool_available(str(row.get("tool_id") or ""))}
            for row in items
        ]
        return {"items": enriched, "count": len(enriched)}
    except SupabaseStoreError as exc:
        logger.warning("list_tools: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/tools/{tool_id}")
async def get_tool_detail(
    tool_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    store = get_tool_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_tool(tool_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Outil '{tool_id}' introuvable.")
        stats = await store.get_stats(tool_id, days=days)
    except SupabaseStoreError as exc:
        logger.warning("get_tool_detail: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        **row,
        "is_available": is_tool_available(tool_id),
        "stats": stats,
    }


@router.get("/tools/{tool_id}/executions")
async def get_tool_executions(
    tool_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    store = get_tool_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        tool = await store.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Outil '{tool_id}' introuvable.")
        stats = await store.get_stats(tool_id, days=days)
    except SupabaseStoreError as exc:
        logger.warning("get_tool_executions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return stats
