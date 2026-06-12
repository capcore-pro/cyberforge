"""
Routes API — LLM usage et agrégats de coûts.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from db.llm_usage_store import get_llm_usage_store
from db.supabase_store import SupabaseStoreError
from llm.llm_usage_service import get_llm_usage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["llm_usage"])


@router.get("/llm-usage/daily")
async def get_daily_llm_usage() -> dict:
    """Agrégat journalier (table cost_tracking)."""
    try:
        return await get_llm_usage_service().get_daily_summary()
    except SupabaseStoreError as exc:
        logger.warning("get_daily_llm_usage: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/llm-usage/generation/{generation_id}")
async def get_generation_llm_usage(generation_id: str) -> dict:
    """Lignes llm_usage pour une génération (SSE id)."""
    store = get_llm_usage_store()
    if not store.is_configured():
        return {"items": [], "generation_id": generation_id}
    try:
        items = await store.list_by_generation(generation_id)
        return {"generation_id": generation_id, "items": items}
    except SupabaseStoreError as exc:
        logger.warning("get_generation_llm_usage: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
