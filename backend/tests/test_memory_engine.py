"""Tests Memory Engine — remember, recall, pipeline (mocks)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from agents.generator_ai import _build_user_message
from api.main import create_app
from memory.memory_service import MemoryService

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SQL = REPO_ROOT / "supabase" / "migrations" / "012_memory_engine.sql"

FAKE_VECTOR = [0.15] * 1536


class _FakeMemoryStore:
    def __init__(self) -> None:
        self.entries: list[dict] = []
        self.embeddings: list[dict] = []
        self._seq = 0

    def is_configured(self) -> bool:
        return True

    async def create_entry(self, **kwargs) -> dict:
        self._seq += 1
        row = {"id": f"mem-{self._seq}", **kwargs}
        self.entries.append(row)
        return row

    async def get_entry(self, memory_id: str) -> dict | None:
        for row in self.entries:
            if row.get("id") == memory_id and not row.get("deleted_at"):
                return row
        return None

    async def list_entries(self, **kwargs) -> list[dict]:
        limit = int(kwargs.get("limit") or 50)
        min_imp = int(kwargs.get("min_importance") or 0)
        rows = [
            r
            for r in self.entries
            if not r.get("deleted_at")
            and int(r.get("importance_score") or 0) >= min_imp
        ]
        rows.sort(
            key=lambda r: (int(r.get("importance_score") or 0), r.get("created_at", "")),
            reverse=True,
        )
        return rows[:limit]

    async def update_entry(self, memory_id: str, updates: dict) -> dict:
        for row in self.entries:
            if row.get("id") == memory_id:
                row.update(updates)
                return row
        raise ValueError("not found")

    async def delete_entry(self, memory_id: str) -> None:
        for row in self.entries:
            if row.get("id") == memory_id:
                row["deleted_at"] = "2026-01-01T00:00:00Z"

    async def increment_access(self, memory_id: str) -> None:
        entry = await self.get_entry(memory_id)
        if entry:
            entry["access_count"] = int(entry.get("access_count") or 0) + 1

    async def create_embedding(self, **kwargs) -> dict:
        row = {"id": f"emb-{len(self.embeddings) + 1}", **kwargs}
        self.embeddings.append(row)
        return row

    async def search_similar(self, query_embedding, **kwargs) -> list[dict]:
        return [
            {
                "memory_id": "mem-1",
                "title": "Préférence client Dupont",
                "content": "Ce client préfère le dark mode et les couleurs marines",
                "memory_type": "long_term",
                "category": "preference",
                "importance_score": 75,
                "similarity": 0.88,
            }
        ]


@pytest.fixture()
def memory_api_client(monkeypatch: pytest.MonkeyPatch):
    store = _FakeMemoryStore()
    monkeypatch.setattr("api.routes.memory.get_memory_store", lambda: store)

    fake_embeddings = AsyncMock()
    fake_embeddings.model = "text-embedding-3-small"
    fake_embeddings.embed_text = AsyncMock(return_value=FAKE_VECTOR)
    fake_embeddings.embed_texts = AsyncMock(
        side_effect=lambda texts: [FAKE_VECTOR for _ in texts]
    )

    service = MemoryService(store=store, embedding_service=fake_embeddings)
    monkeypatch.setattr("api.routes.memory.get_memory_service", lambda: service)
    monkeypatch.setattr("memory.memory_service.get_memory_service", lambda: service)

    app = create_app()
    with TestClient(app) as client:
        yield client, store, fake_embeddings


def test_remember_api_creates_entry_and_embedding(memory_api_client) -> None:
    client, store, _embed = memory_api_client
    res = client.post(
        "/api/memory/remember",
        json={
            "title": "Préférence client Dupont",
            "content": "Ce client préfère le dark mode et les couleurs marines",
            "category": "preference",
            "importance_score": 75,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "stored"
    assert len(store.entries) == 1
    assert store.entries[0]["memory_type"] == "long_term"
    assert len(store.embeddings) == 1


def test_recall_api_returns_similarity_scores(memory_api_client) -> None:
    client, _store, _embed = memory_api_client
    res = client.post(
        "/api/memory/recall",
        json={"query": "préférences visuelles client", "limit": 5},
    )
    assert res.status_code == 200, res.text
    hits = res.json()
    assert len(hits) == 1
    assert hits[0]["similarity"] == pytest.approx(0.88)
    assert "marines" in hits[0]["content"]


def test_remember_generation_automatic() -> None:
    store = _FakeMemoryStore()
    embeddings = AsyncMock()
    embeddings.model = "text-embedding-3-small"
    embeddings.embed_text = AsyncMock(return_value=FAKE_VECTOR)
    service = MemoryService(store=store, embedding_service=embeddings)

    brief = {
        "project_type": "vitrine_next",
        "client_name": "Dupont",
        "sector": "boulangerie",
        "couleur_primaire": "#003366",
        "design_system": {"style_family": "premium"},
    }
    result = asyncio.run(
        service.remember_generation(
            brief=brief,
            result={"url": "https://demo.test", "duration_ms": 42000},
        )
    )
    assert result["status"] == "stored"
    assert len(store.entries) == 1
    assert store.entries[0]["memory_type"] == "project"
    assert store.entries[0]["importance_score"] == 80
    assert store.entries[0]["category"] == "generation"


def test_generator_includes_memory_context() -> None:
    brief = {
        "client_name": "Test",
        "project_type": "vitrine_next",
        "memory_context": "## Contexte Mémoire\n\n### Préférence\nDark mode",
    }
    msg = _build_user_message(brief)
    assert "## memory_context" in msg
    assert "Dark mode" in msg


def test_generator_graceful_without_memory_context() -> None:
    brief = {"client_name": "Test", "project_type": "vitrine_next"}
    msg = _build_user_message(brief)
    assert "## memory_context" not in msg


def test_recall_fallback_without_openai() -> None:
    store = _FakeMemoryStore()
    asyncio.run(
        store.create_entry(
            title="Fallback",
            content="Mémoire sans embedding",
            memory_type="long_term",
            importance_score=60,
        )
    )
    embeddings = AsyncMock()
    embeddings.embed_text = AsyncMock(side_effect=ValueError("OPENAI_API_KEY absente"))
    service = MemoryService(store=store, embedding_service=embeddings)

    hits = asyncio.run(service.recall("test", limit=5))
    assert len(hits) == 1
    assert hits[0]["similarity"] == 0.0


def test_migration_sql_defines_memory_schema() -> None:
    assert MIGRATION_SQL.is_file()
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for name in (
        "memory_entries",
        "memory_embeddings",
        "search_memories",
    ):
        assert name in sql
