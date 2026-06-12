"""
Routes API — Supervisor System (stats, quality, planning).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agents.planning_engine import PlanningEngine
from db.supabase_store import SupabaseStoreError
from db.supervisor_store import get_supervisor_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["supervisor"])


class PlanRequest(BaseModel):
    brief: dict = Field(default_factory=dict)


@router.get("/supervisor/stats")
async def get_supervisor_stats(days: int = Query(default=30, ge=1, le=365)) -> dict:
    store = get_supervisor_store()
    if not store.is_configured():
        return {
            "days": days,
            "total_validations": 0,
            "pass_rate": 0.0,
            "avg_quality_score": 0.0,
            "avg_attempts": 0.0,
        }
    try:
        return await store.get_supervisor_stats(days=days)
    except SupabaseStoreError as exc:
        logger.warning("get_supervisor_stats: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/supervisor/quality/{generation_id}")
async def get_generation_quality(generation_id: str) -> dict:
    store = get_supervisor_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        return await store.get_generation_score(generation_id)
    except SupabaseStoreError as exc:
        logger.warning("get_generation_quality: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/supervisor/plan")
async def build_execution_plan(body: PlanRequest) -> dict:
    plan = PlanningEngine().build_plan(body.brief or {})
    return plan
