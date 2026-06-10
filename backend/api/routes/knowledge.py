"""
Routes API — Knowledge Engine (ingestion, recherche, documents).
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from db.knowledge_store import get_knowledge_store
from db.supabase_store import SupabaseStoreError
from knowledge.knowledge_service import get_knowledge_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge"])

ALLOWED_UPLOAD_SUFFIXES = {".txt", ".md"}


class IngestTextRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    project_id: str | None = Field(default=None, max_length=128)
    source_type: str = Field(default="manual", max_length=100)


class IngestTextResponse(BaseModel):
    document_id: str
    chunks_count: int
    status: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    project_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    chunk_id: str | None = None
    document_id: str | None = None
    document_title: str | None = None
    content: str | None = None
    similarity: float = 0.0


class KnowledgeDocumentSummary(BaseModel):
    id: str
    title: str
    source_type: str | None = None
    project_id: str | None = None
    language: str | None = None
    status: str | None = None
    created_at: str | None = None


@router.post("/knowledge/ingest", response_model=IngestTextResponse)
async def ingest_knowledge_text(body: IngestTextRequest) -> IngestTextResponse:
    store = get_knowledge_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    service = get_knowledge_service()
    try:
        result = await service.ingest_text(
            title=body.title,
            content=body.content,
            project_id=body.project_id,
            source_type=body.source_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return IngestTextResponse(**result)


@router.post("/knowledge/ingest-file", response_model=IngestTextResponse)
async def ingest_knowledge_file(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    project_id: str | None = Form(default=None),
) -> IngestTextResponse:
    store = get_knowledge_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    filename = (file.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail="Formats acceptés : .txt, .md")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    service = get_knowledge_service()
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
            mode="wb",
        ) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        result = await service.ingest_file(
            tmp_path,
            title=(title or Path(filename).stem).strip() or "Document",
            project_id=(project_id or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Impossible de supprimer le fichier temporaire %s", tmp_path)

    return IngestTextResponse(**result)


@router.post("/knowledge/search", response_model=list[SearchHit])
async def search_knowledge(body: SearchRequest) -> list[SearchHit]:
    store = get_knowledge_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    service = get_knowledge_service()
    try:
        hits = await service.search(
            body.query,
            project_id=body.project_id,
            limit=body.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return [SearchHit(**h) for h in hits]


@router.get("/knowledge/documents", response_model=list[KnowledgeDocumentSummary])
async def list_knowledge_documents(
    project_id: str | None = None,
    limit: int = 50,
) -> list[KnowledgeDocumentSummary]:
    store = get_knowledge_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    rows = await store.list_documents(project_id=project_id, limit=limit)
    return [
        KnowledgeDocumentSummary(
            id=str(row.get("id")),
            title=str(row.get("title") or ""),
            source_type=row.get("source_type"),
            project_id=row.get("project_id"),
            language=row.get("language"),
            status=row.get("status"),
            created_at=row.get("created_at"),
        )
        for row in rows
        if isinstance(row, dict) and row.get("id")
    ]


@router.delete("/knowledge/documents/{document_id}")
async def delete_knowledge_document(document_id: str) -> dict[str, bool]:
    store = get_knowledge_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    existing = await store.get_document(document_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    try:
        await store.delete_document(document_id)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True}
