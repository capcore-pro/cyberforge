"""
Routes API — Memory Engine (remember, recall, entrées).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.memory_store import get_memory_store
from db.supabase_store import SupabaseStoreError
from memory.memory_service import get_memory_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])


class RememberRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    category: str = Field(default="preference", max_length=100)
    importance_score: int = Field(default=70, ge=0, le=100)
    project_id: str | None = Field(default=None, max_length=128)


class RememberResponse(BaseModel):
    memory_id: str
    title: str | None = None
    status: str


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    project_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=10, ge=1, le=50)
    min_importance: int = Field(default=0, ge=0, le=100)


class RecallHit(BaseModel):
    memory_id: str | None = None
    title: str | None = None
    content: str | None = None
    memory_type: str | None = None
    category: str | None = None
    importance_score: int | None = None
    similarity: float = 0.0


class MemoryEntrySummary(BaseModel):
    id: str
    title: str
    memory_type: str | None = None
    category: str | None = None
    importance_score: int | None = None
    project_id: str | None = None
    access_count: int | None = None
    created_at: str | None = None


@router.post("/memory/remember", response_model=RememberResponse)
async def remember_memory(body: RememberRequest) -> RememberResponse:
    store = get_memory_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    service = get_memory_service()
    try:
        result = await service.remember_manual(
            title=body.title,
            content=body.content,
            category=body.category,
            importance_score=body.importance_score,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RememberResponse(**result)


@router.post("/memory/recall", response_model=list[RecallHit])
async def recall_memory(body: RecallRequest) -> list[RecallHit]:
    store = get_memory_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    service = get_memory_service()
    try:
        hits = await service.recall(
            body.query,
            project_id=body.project_id,
            limit=body.limit,
            min_importance=body.min_importance,
        )
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return [RecallHit(**h) for h in hits]


@router.get("/memory/entries", response_model=list[MemoryEntrySummary])
async def list_memory_entries(
    project_id: str | None = None,
    memory_type: str | None = None,
    limit: int = 50,
) -> list[MemoryEntrySummary]:
    store = get_memory_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    rows = await store.list_entries(
        project_id=project_id,
        memory_type=memory_type,
        limit=limit,
    )
    return [
        MemoryEntrySummary(
            id=str(row.get("id")),
            title=str(row.get("title") or ""),
            memory_type=row.get("memory_type"),
            category=row.get("category"),
            importance_score=row.get("importance_score"),
            project_id=row.get("project_id"),
            access_count=row.get("access_count"),
            created_at=row.get("created_at"),
        )
        for row in rows
        if isinstance(row, dict) and row.get("id")
    ]


@router.delete("/memory/entries/{memory_id}")
async def delete_memory_entry(memory_id: str) -> dict[str, bool]:
    store = get_memory_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    existing = await store.get_entry(memory_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Mémoire introuvable.")

    try:
        await store.delete_entry(memory_id)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True}
