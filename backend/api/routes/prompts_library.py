"""
Routes API — Bibliothèque de prompts (Volume 3).
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
