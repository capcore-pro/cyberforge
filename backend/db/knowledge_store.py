"""
Persistance Supabase — Knowledge Engine (documents, chunks, embeddings).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

DOCUMENT_SELECT = (
    "id,project_id,organization_id,title,source_type,language,"
    "file_path,content,content_hash,status,created_at,updated_at,deleted_at"
)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


class KnowledgeStore:
    """CRUD PostgREST pour knowledge_documents / chunks / embeddings."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def create_document(
        self,
        *,
        title: str,
        content: str,
        source_type: str = "manual",
        project_id: str | None = None,
        language: str = "fr",
        file_path: str | None = None,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "title": title.strip(),
            "content": content,
            "source_type": source_type,
            "language": language,
            "status": "active",
            "organization_id": DEFAULT_ORG_ID,
        }
        if project_id:
            body["project_id"] = project_id
        if file_path:
            body["file_path"] = file_path
        if content_hash:
            body["content_hash"] = content_hash

        url = f"{self._rest_url()}/knowledge_documents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_document", "POST", url, self._supabase)
            _raise_for_status(resp, "create_document", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création document sans identifiant retourné.")
            return row

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not document_id.strip():
            return None

        url = f"{self._rest_url()}/knowledge_documents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{document_id}",
                    "deleted_at": "is.null",
                    "select": DOCUMENT_SELECT,
                },
            )
            _raise_for_status(resp, "get_document", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return rows[0]

    async def list_documents(
        self,
        *,
        project_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": DOCUMENT_SELECT,
            "deleted_at": "is.null",
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 200))),
        }
        if project_id:
            params["project_id"] = f"eq.{project_id}"

        url = f"{self._rest_url()}/knowledge_documents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params=params,
            )
            _raise_for_status(resp, "list_documents", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def delete_document(self, document_id: str) -> None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/knowledge_documents"
        now = datetime.now(UTC).isoformat()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{document_id}"},
                json={"deleted_at": now, "updated_at": now, "status": "deleted"},
            )
            _raise_for_status(resp, "delete_document", "PATCH", url, self._supabase)

    async def create_chunk(
        self,
        *,
        document_id: str,
        chunk_index: int,
        content: str,
        token_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content": content,
        }
        if token_count is not None:
            body["token_count"] = token_count
        if metadata:
            body["metadata"] = metadata

        url = f"{self._rest_url()}/knowledge_chunks"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers("return=representation"),
                json=body,
            )
            _raise_for_status(resp, "create_chunk", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création chunk sans identifiant retourné.")
            return row

    async def create_embedding(
        self,
        *,
        chunk_id: str,
        document_id: str,
        project_id: str | None,
        embedding: list[float],
        embedding_model: str = "text-embedding-3-small",
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "organization_id": DEFAULT_ORG_ID,
            "embedding_model": embedding_model,
            "embedding": _vector_literal(embedding),
        }
        if project_id:
            body["project_id"] = project_id

        url = f"{self._rest_url()}/knowledge_embeddings"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers("return=representation"),
                json=body,
            )
            _raise_for_status(resp, "create_embedding", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création embedding sans identifiant retourné.")
            return row

    async def search_similar(
        self,
        query_embedding: list[float],
        *,
        project_id: str | None = None,
        limit: int = 10,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        body: dict[str, Any] = {
            "query_embedding": _vector_literal(query_embedding),
            "match_org_id": organization_id,
            "match_count": max(1, min(limit, 50)),
        }
        if project_id:
            body["match_project_id"] = project_id

        url = f"{self._rest_url()}/rpc/search_knowledge"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers(),
                json=body,
            )
            _raise_for_status(resp, "search_similar", "POST", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def search_hybrid(
        self,
        query_embedding: list[float],
        query_text: str,
        *,
        project_id: str | None = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        body: dict[str, Any] = {
            "query_embedding": _vector_literal(query_embedding),
            "query_text": query_text.strip(),
            "match_org_id": organization_id,
            "match_count": max(1, min(limit, 50)),
            "vector_weight": float(vector_weight),
            "keyword_weight": float(keyword_weight),
        }
        if project_id:
            body["match_project_id"] = project_id

        url = f"{self._rest_url()}/rpc/search_knowledge_hybrid"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers(),
                json=body,
            )
            _raise_for_status(resp, "search_hybrid", "POST", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []


_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store


def reset_knowledge_store() -> None:
    global _store
    _store = None
