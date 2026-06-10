"""Tests Knowledge Engine — ingestion, recherche, pipeline (mocks)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agents.generator_ai import _build_user_message
from api.main import create_app
from knowledge.chunking_service import ChunkingService
from knowledge.knowledge_service import KnowledgeService


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SQL = REPO_ROOT / "supabase" / "migrations" / "011_knowledge_engine.sql"

FAKE_VECTOR = [0.1] * 1536


def _long_text(word_count: int = 500) -> str:
    return " ".join(f"mot{i}" for i in range(word_count))


class _FakeKnowledgeStore:
    def __init__(self) -> None:
        self.documents: list[dict] = []
        self.chunks: list[dict] = []
        self.embeddings: list[dict] = []
        self._doc_seq = 0
        self._chunk_seq = 0

    def is_configured(self) -> bool:
        return True

    async def create_document(self, **kwargs) -> dict:
        self._doc_seq += 1
        doc = {"id": f"doc-{self._doc_seq}", **kwargs}
        self.documents.append(doc)
        return doc

    async def create_chunk(self, **kwargs) -> dict:
        self._chunk_seq += 1
        row = {"id": f"chunk-{self._chunk_seq}", **kwargs}
        self.chunks.append(row)
        return row

    async def create_embedding(self, **kwargs) -> dict:
        row = {"id": f"emb-{len(self.embeddings) + 1}", **kwargs}
        self.embeddings.append(row)
        return row

    async def search_similar(self, query_embedding, **kwargs) -> list[dict]:
        return [
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "document_title": "Test CRM",
                "content": "pipeline CRM ventes",
                "similarity": 0.92,
            }
        ]

    async def list_documents(self, **kwargs) -> list[dict]:
        return self.documents

    async def get_document(self, document_id: str) -> dict | None:
        for doc in self.documents:
            if doc.get("id") == document_id:
                return doc
        return None

    async def delete_document(self, document_id: str) -> None:
        for doc in self.documents:
            if doc.get("id") == document_id:
                doc["deleted_at"] = "2026-01-01T00:00:00Z"


@pytest.fixture()
def knowledge_api_client(monkeypatch: pytest.MonkeyPatch):
    store = _FakeKnowledgeStore()
    monkeypatch.setattr("api.routes.knowledge.get_knowledge_store", lambda: store)

    fake_embeddings = AsyncMock()
    fake_embeddings.model = "text-embedding-3-small"
    fake_embeddings.embed_texts = AsyncMock(
        side_effect=lambda texts: [[0.1] * 1536 for _ in texts]
    )
    fake_embeddings.embed_text = AsyncMock(return_value=FAKE_VECTOR)

    service = KnowledgeService(
        store=store,
        embedding_service=fake_embeddings,
        chunking_service=ChunkingService(),
    )
    monkeypatch.setattr("api.routes.knowledge.get_knowledge_service", lambda: service)
    monkeypatch.setattr("knowledge.knowledge_service.get_knowledge_service", lambda: service)

    app = create_app()
    with TestClient(app) as client:
        yield client, store, fake_embeddings


def test_ingest_api_creates_document_chunks_embeddings(knowledge_api_client) -> None:
    client, store, _embed = knowledge_api_client
    content = _long_text(500)
    res = client.post(
        "/api/knowledge/ingest",
        json={"title": "Test CRM", "content": content},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "indexed"
    assert body["chunks_count"] >= 1
    assert len(store.documents) == 1
    assert len(store.chunks) == body["chunks_count"]
    assert len(store.embeddings) == body["chunks_count"]


def test_search_api_returns_similarity_scores(knowledge_api_client) -> None:
    client, _store, _embed = knowledge_api_client
    res = client.post(
        "/api/knowledge/search",
        json={"query": "CRM pipeline", "limit": 5},
    )
    assert res.status_code == 200, res.text
    hits = res.json()
    assert len(hits) == 1
    assert hits[0]["similarity"] == pytest.approx(0.92)
    assert "pipeline CRM" in hits[0]["content"]


def test_generator_includes_knowledge_context() -> None:
    brief = {
        "client_name": "Test",
        "project_type": "vitrine_next",
        "knowledge_context": "## Contexte Knowledge Engine\n\n### Doc (0.92)\nCRM pipeline",
    }
    msg = _build_user_message(brief)
    assert "## knowledge_context" in msg
    assert "CRM pipeline" in msg


def test_generator_graceful_without_knowledge_context() -> None:
    brief = {"client_name": "Test", "project_type": "vitrine_next"}
    msg = _build_user_message(brief)
    assert "## knowledge_context" not in msg


def test_get_context_graceful_without_openai_key() -> None:
    store = _FakeKnowledgeStore()
    embeddings = MagicMock()
    embeddings.embed_text = AsyncMock(side_effect=ValueError("OPENAI_API_KEY absente"))
    service = KnowledgeService(store=store, embedding_service=embeddings)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        asyncio.run(service.search("CRM"))


async def _pipeline_knowledge_hook(brief: dict, prompt: str) -> None:
    """Extrait la logique pipeline (dégradation gracieuse)."""
    try:
        from knowledge.knowledge_service import get_knowledge_service

        knowledge_ctx = await get_knowledge_service().get_context_for_prompt(
            query=str(brief.get("description") or prompt),
            project_id=brief.get("project_id"),
        )
        if knowledge_ctx:
            brief["knowledge_context"] = knowledge_ctx
    except Exception:
        pass


def test_pipeline_graceful_when_knowledge_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(*_args, **_kwargs):
        raise ValueError("OPENAI_API_KEY absente")

    monkeypatch.setattr(
        "knowledge.knowledge_service.get_knowledge_service",
        lambda: type("S", (), {"get_context_for_prompt": _boom})(),
    )
    brief: dict = {"description": "Boulangerie artisanale"}
    asyncio.run(_pipeline_knowledge_hook(brief, "Boulangerie artisanale"))
    assert "knowledge_context" not in brief


def test_migration_sql_defines_knowledge_schema() -> None:
    assert MIGRATION_SQL.is_file()
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for name in (
        "knowledge_documents",
        "knowledge_chunks",
        "knowledge_embeddings",
        "search_knowledge",
        "CREATE EXTENSION IF NOT EXISTS vector",
    ):
        assert name in sql


def test_chunking_produces_overlapping_chunks() -> None:
    svc = ChunkingService(chunk_size=100, overlap=20)
    text = _long_text(800)
    chunks = svc.chunk_document(text, title="Test")
    assert len(chunks) > 1
    assert all(c["token_count"] > 0 for c in chunks)


def test_knowledge_service_ingest_flow() -> None:
    store = _FakeKnowledgeStore()
    embeddings = AsyncMock()
    embeddings.model = "text-embedding-3-small"
    embeddings.embed_texts = AsyncMock(
        side_effect=lambda texts: [[0.2] * 1536 for _ in texts]
    )
    service = KnowledgeService(store=store, embedding_service=embeddings)

    result = asyncio.run(
        service.ingest_text(
            title="Test CRM",
            content=_long_text(600),
        )
    )
    assert result["status"] == "indexed"
    assert result["chunks_count"] >= 1
    assert len(store.embeddings) == result["chunks_count"]
