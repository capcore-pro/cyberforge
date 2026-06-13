"""
Routes API — Bibliothèque de prompts (Volume 3 + 04D).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.prompt_store import get_prompt_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prompts_library"])


class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    category_slug: str = Field(..., min_length=1, max_length=255)
    agent_slug: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class UpdatePromptRequest(BaseModel):
    content: str = Field(..., min_length=1)
    changelog: str | None = Field(default=None, max_length=2000)


class RollbackRequest(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)


class QualityScoreRequest(BaseModel):
    score: int = Field(..., ge=0, le=100)


class BenchmarkRequest(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=100)
    model_used: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    quality_score: int = Field(..., ge=0, le=100)
    cost_usd: float = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class ABTestRequest(BaseModel):
    prompt_slug_a: str = Field(..., min_length=1, max_length=255)
    prompt_slug_b: str = Field(..., min_length=1, max_length=255)
    min_samples: int = Field(default=3, ge=1, le=50)


@router.get("/prompts-library")
async def list_prompts(
    category: str | None = Query(default=None, alias="category"),
    agent: str | None = Query(default=None),
    status: str = Query(default="active"),
) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_all(category_slug=category, status=status)
        if agent:
            items = [p for p in items if p.get("agent_slug") == agent]
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_prompts: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/categories")
async def list_prompt_categories() -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_categories()
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_prompt_categories: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/best/{task_type}")
async def get_best_prompt(task_type: str) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        row = await store.get_best_prompt_for_task(task_type)
        if not row:
            raise HTTPException(status_code=404, detail="Aucun prompt pour cette tâche")
        return row
    except SupabaseStoreError as exc:
        logger.warning("get_best_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts-library/ab-test")
async def compare_prompts_ab_test(body: ABTestRequest) -> dict:
    from agents.ab_testing_engine import ab_testing_engine

    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await ab_testing_engine.compare(
            prompt_slug_a=body.prompt_slug_a,
            prompt_slug_b=body.prompt_slug_b,
            min_samples=body.min_samples,
        )
    except SupabaseStoreError as exc:
        logger.warning("compare_prompts_ab_test: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts-library")
async def create_prompt(body: CreatePromptRequest) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await store.create(
            name=body.name,
            slug=body.slug,
            content=body.content,
            category_slug=body.category_slug,
            agent_slug=body.agent_slug,
            description=body.description,
        )
    except SupabaseStoreError as exc:
        logger.warning("create_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/{prompt_id}/versions")
async def list_prompt_versions(prompt_id: str) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        items = await store.list_versions(prompt_id)
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_prompt_versions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/{prompt_id}/versions/{version}")
async def get_prompt_version(prompt_id: str, version: str) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        row = await store.get_version(prompt_id, version)
        if not row:
            raise HTTPException(status_code=404, detail="Version introuvable")
        return row
    except SupabaseStoreError as exc:
        logger.warning("get_prompt_version: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts-library/{prompt_id}/rollback")
async def rollback_prompt(prompt_id: str, body: RollbackRequest) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await store.rollback(prompt_id, body.version)
    except SupabaseStoreError as exc:
        logger.warning("rollback_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/prompts-library/{prompt_id}/quality")
async def update_prompt_quality(prompt_id: str, body: QualityScoreRequest) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await store.update_quality_score(prompt_id, body.score)
    except SupabaseStoreError as exc:
        logger.warning("update_prompt_quality: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts-library/{prompt_id}/archive")
async def archive_prompt(prompt_id: str) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await store.archive(prompt_id)
    except SupabaseStoreError as exc:
        logger.warning("archive_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts-library/{prompt_id}/benchmark")
async def add_prompt_benchmark(prompt_id: str, body: BenchmarkRequest) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        prompt = await store.get_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt introuvable")
        benchmark = await store.add_benchmark(
            prompt_id,
            str(prompt.get("version") or ""),
            body.task_type,
            body.model_used,
            body.provider,
            body.input_tokens,
            body.output_tokens,
            body.duration_ms,
            body.quality_score,
            body.cost_usd,
            notes=body.notes,
        )
        benchmarks = await store.list_benchmarks(prompt_id=prompt_id, limit=200)
        if benchmarks:
            avg = sum(int(b.get("quality_score") or 0) for b in benchmarks) / len(
                benchmarks
            )
            await store.update_quality_score(prompt_id, int(round(avg)))
        return benchmark
    except SupabaseStoreError as exc:
        logger.warning("add_prompt_benchmark: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/{prompt_id}/benchmarks")
async def list_prompt_benchmarks(
    prompt_id: str,
    task_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_benchmarks(
            prompt_id=prompt_id,
            task_type=task_type,
            limit=limit,
        )
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_prompt_benchmarks: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/prompts-library/{prompt_id}")
async def update_prompt(prompt_id: str, body: UpdatePromptRequest) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        return await store.update_content(
            prompt_id,
            body.content,
            changelog=body.changelog,
        )
    except SupabaseStoreError as exc:
        logger.warning("update_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prompts-library/{slug}")
async def get_prompt(slug: str) -> dict:
    store = get_prompt_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré")
    try:
        row = await store.get_by_slug(slug)
        if not row:
            raise HTTPException(status_code=404, detail="Prompt introuvable")
        return row
    except SupabaseStoreError as exc:
        logger.warning("get_prompt: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
