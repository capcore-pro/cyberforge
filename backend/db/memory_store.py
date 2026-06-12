"""
Persistance Supabase — Memory Engine (entrées + embeddings).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from db.knowledge_store import _first_row, _vector_literal
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

ENTRY_SELECT = (
    "id,project_id,organization_id,agent_id,memory_type,category,title,content,"
    "importance_score,relevance_score,access_count,last_accessed_at,"
    "created_at,updated_at,deleted_at"
)


class MemoryStore:
    """CRUD PostgREST pour memory_entries / memory_embeddings."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def create_entry(
        self,
        *,
        title: str,
        content: str,
        memory_type: str,
        category: str = "general",
        importance_score: int = 50,
        relevance_score: int = 50,
        project_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "title": title.strip(),
            "content": content,
            "memory_type": memory_type,
            "category": category,
            "importance_score": importance_score,
            "relevance_score": relevance_score,
            "organization_id": DEFAULT_ORG_ID,
        }
        if project_id:
            body["project_id"] = project_id
        if agent_id:
            body["agent_id"] = agent_id

        url = f"{self._rest_url()}/memory_entries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_entry", "POST", url, self._supabase)
            _raise_for_status(resp, "create_entry", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création mémoire sans identifiant retourné.")
            return row

    async def get_entry(self, memory_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not memory_id.strip():
            return None

        url = f"{self._rest_url()}/memory_entries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{memory_id}",
                    "deleted_at": "is.null",
                    "select": ENTRY_SELECT,
                },
            )
            _raise_for_status(resp, "get_entry", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return rows[0]

    async def list_entries(
        self,
        *,
        project_id: str | None = None,
        memory_type: str | None = None,
        min_importance: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": ENTRY_SELECT,
            "deleted_at": "is.null",
            "importance_score": f"gte.{min_importance}",
            "order": "importance_score.desc,created_at.desc",
            "limit": str(max(1, min(limit, 200))),
        }
        if project_id:
            params["project_id"] = f"eq.{project_id}"
        if memory_type:
            params["memory_type"] = f"eq.{memory_type}"

        url = f"{self._rest_url()}/memory_entries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params=params,
            )
            _raise_for_status(resp, "list_entries", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def update_entry(self, memory_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        payload = {**updates, "updated_at": datetime.now(UTC).isoformat()}
        url = f"{self._rest_url()}/memory_entries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{memory_id}"},
                json=payload,
            )
            _raise_for_status(resp, "update_entry", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Mise à jour mémoire sans retour.")
            return row

    async def delete_entry(self, memory_id: str) -> None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        now = datetime.now(UTC).isoformat()
        url = f"{self._rest_url()}/memory_entries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{memory_id}"},
                json={"deleted_at": now, "updated_at": now},
            )
            _raise_for_status(resp, "delete_entry", "PATCH", url, self._supabase)

    async def increment_access(self, memory_id: str) -> None:
        entry = await self.get_entry(memory_id)
        if not entry:
            return
        count = int(entry.get("access_count") or 0) + 1
        now = datetime.now(UTC).isoformat()
        await self.update_entry(
            memory_id,
            {"access_count": count, "last_accessed_at": now},
        )

    async def create_embedding(
        self,
        *,
        memory_entry_id: str,
        project_id: str | None,
        embedding: list[float],
        embedding_model: str = "text-embedding-3-small",
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "memory_entry_id": memory_entry_id,
            "organization_id": DEFAULT_ORG_ID,
            "embedding_model": embedding_model,
            "embedding": _vector_literal(embedding),
        }
        if project_id:
            body["project_id"] = project_id

        url = f"{self._rest_url()}/memory_embeddings"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers("return=representation"),
                json=body,
            )
            _raise_for_status(resp, "create_embedding", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création embedding mémoire sans identifiant.")
            return row

    async def search_similar(
        self,
        query_embedding: list[float],
        *,
        project_id: str | None = None,
        limit: int = 10,
        min_importance: int = 0,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        body: dict[str, Any] = {
            "query_embedding": _vector_literal(query_embedding),
            "match_org_id": organization_id,
            "match_count": max(1, min(limit, 50)),
            "min_importance": min_importance,
        }
        if project_id:
            body["match_project_id"] = project_id

        url = f"{self._rest_url()}/rpc/search_memories"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers(),
                json=body,
            )
            _raise_for_status(resp, "search_similar", "POST", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def reset_memory_store() -> None:
    global _store
    _store = None
