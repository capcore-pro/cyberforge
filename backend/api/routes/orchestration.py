"""
Routes API — Multi-Agent Orchestration (sessions, messages, stats).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from db.orchestration_store import get_orchestration_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orchestration"])


@router.get("/orchestration/sessions")
async def list_orchestration_sessions(
    project_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_sessions(
            project_id=project_id,
            status=status,
            limit=limit,
        )
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_orchestration_sessions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/orchestration/sessions/{generation_id}")
async def get_orchestration_session(generation_id: str) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        session = await store.get_session(generation_id)
    except SupabaseStoreError as exc:
        logger.warning("get_orchestration_session: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session orchestration pour '{generation_id}' introuvable.",
        )
    contexts = await store.list_shared_contexts(str(session.get("id") or ""))
    return {**session, "shared_contexts": contexts}


@router.get("/orchestration/sessions/{generation_id}/messages")
async def get_orchestration_messages(
    generation_id: str,
    receiver_agent: str | None = Query(default=None),
) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        session = await store.get_session(generation_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session orchestration pour '{generation_id}' introuvable.",
            )
        messages = await store.get_messages(
            str(session["id"]),
            receiver_agent=receiver_agent,
        )
        return {"items": messages, "count": len(messages)}
    except SupabaseStoreError as exc:
        logger.warning("get_orchestration_messages: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/orchestration/stats")
async def get_orchestration_stats() -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        return {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "avg_agents_per_session": 0.0,
            "parallel_executions_count": 0,
        }
    try:
        return await store.get_stats()
    except SupabaseStoreError as exc:
        logger.warning("get_orchestration_stats: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
