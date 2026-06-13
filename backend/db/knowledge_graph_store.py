"""
Persistance Supabase — Knowledge Graph (nœuds et arêtes).
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

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

NODE_TYPES = frozenset(
    {
        "agent",
        "project",
        "client",
        "document",
        "workflow",
        "tool",
        "prompt",
        "memory",
    }
)

RELATION_TYPES = frozenset(
    {
        "uses",
        "belongs_to",
        "indexed_for",
        "executes",
        "generated_by",
        "references",
        "benchmarks",
        "triggers",
    }
)

NODE_SELECT = (
    "id,entity_type,entity_id,label,properties,organization_id,"
    "created_at,updated_at"
)

EDGE_SELECT = (
    "id,source_type,source_id,target_type,target_id,relation_type,"
    "weight,properties,created_at"
)

NeighborDirection = Literal["outgoing", "incoming", "both"]


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


class KnowledgeGraphStore:
    """CRUD PostgREST pour knowledge_graph_nodes / knowledge_graph_edges."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def upsert_node(
        self,
        entity_type: str,
        entity_id: str,
        label: str,
        properties: dict | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "entity_type": entity_type.strip(),
            "entity_id": str(entity_id).strip(),
            "label": label.strip() or str(entity_id).strip(),
            "properties": properties or {},
            "organization_id": DEFAULT_ORG_ID,
            "updated_at": _now_iso(),
        }

        url = f"{self._rest_url()}/knowledge_graph_nodes"
        headers = self._supabase._headers(
            "return=representation,resolution=merge-duplicates"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=headers,
                    params={"on_conflict": "entity_type,entity_id"},
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(
                    exc, "upsert_node", "POST", url, self._supabase
                )
            _raise_for_status(resp, "upsert_node", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Upsert nœud sans identifiant retourné.")
            return row

    async def upsert_edge(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        properties: dict | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "source_type": source_type.strip(),
            "source_id": str(source_id).strip(),
            "target_type": target_type.strip(),
            "target_id": str(target_id).strip(),
            "relation_type": relation_type.strip(),
            "weight": float(weight),
            "properties": properties or {},
        }

        url = f"{self._rest_url()}/knowledge_graph_edges"
        headers = self._supabase._headers(
            "return=representation,resolution=merge-duplicates"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=headers,
                    params={
                        "on_conflict": (
                            "source_type,source_id,target_type,target_id,relation_type"
                        )
                    },
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(
                    exc, "upsert_edge", "POST", url, self._supabase
                )
            _raise_for_status(resp, "upsert_edge", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Upsert arête sans identifiant retourné.")
            return row

    async def get_neighbors(
        self,
        entity_type: str,
        entity_id: str,
        relation_type: str | None = None,
        direction: NeighborDirection = "outgoing",
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        results: list[dict[str, Any]] = []
        url = f"{self._rest_url()}/knowledge_graph_edges"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if direction in ("outgoing", "both"):
                params: dict[str, str] = {
                    "select": EDGE_SELECT,
                    "source_type": f"eq.{entity_type.strip()}",
                    "source_id": f"eq.{str(entity_id).strip()}",
                    "order": "relation_type.asc",
                }
                if relation_type:
                    params["relation_type"] = f"eq.{relation_type.strip()}"
                resp = await client.get(
                    url, headers=self._supabase._headers(), params=params
                )
                _raise_for_status(resp, "get_neighbors_out", "GET", url, self._supabase)
                rows = resp.json()
                if isinstance(rows, list):
                    results.extend(rows)

            if direction in ("incoming", "both"):
                params = {
                    "select": EDGE_SELECT,
                    "target_type": f"eq.{entity_type.strip()}",
                    "target_id": f"eq.{str(entity_id).strip()}",
                    "order": "relation_type.asc",
                }
                if relation_type:
                    params["relation_type"] = f"eq.{relation_type.strip()}"
                resp = await client.get(
                    url, headers=self._supabase._headers(), params=params
                )
                _raise_for_status(resp, "get_neighbors_in", "GET", url, self._supabase)
                rows = resp.json()
                if isinstance(rows, list):
                    results.extend(rows)

        return results

    async def traverse(
        self,
        entity_type: str,
        entity_id: str,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/rpc/traverse_knowledge_graph"
        body = {
            "start_entity_type": entity_type.strip(),
            "start_entity_id": str(entity_id).strip(),
            "max_depth": max(1, min(max_depth, 10)),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers(),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "traverse", "POST", url, self._supabase)
            _raise_for_status(resp, "traverse", "POST", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def list_nodes(
        self,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": NODE_SELECT,
            "order": "entity_type.asc,label.asc",
            "limit": str(max(1, min(limit, 500))),
        }
        if entity_type:
            params["entity_type"] = f"eq.{entity_type.strip()}"

        url = f"{self._rest_url()}/knowledge_graph_nodes"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url, headers=self._supabase._headers(), params=params
            )
            _raise_for_status(resp, "list_nodes", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def list_edges(self, limit: int = 500) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/knowledge_graph_edges"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "select": EDGE_SELECT,
                    "order": "relation_type.asc",
                    "limit": str(max(1, min(limit, 2000))),
                },
            )
            _raise_for_status(resp, "list_edges", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_node(
        self,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        url = f"{self._rest_url()}/knowledge_graph_nodes"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "entity_type": f"eq.{entity_type.strip()}",
                    "entity_id": f"eq.{str(entity_id).strip()}",
                    "select": NODE_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_node", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def delete_node(self, entity_type: str, entity_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        et = entity_type.strip()
        eid = str(entity_id).strip()
        edges_url = f"{self._rest_url()}/knowledge_graph_edges"
        nodes_url = f"{self._rest_url()}/knowledge_graph_nodes"

        async with httpx.AsyncClient(timeout=30.0) as client:
            for params in (
                {"source_type": f"eq.{et}", "source_id": f"eq.{eid}"},
                {"target_type": f"eq.{et}", "target_id": f"eq.{eid}"},
            ):
                resp = await client.delete(
                    edges_url,
                    headers=self._supabase._headers(),
                    params=params,
                )
                _raise_for_status(
                    resp, "delete_node_edges", "DELETE", edges_url, self._supabase
                )

            resp = await client.delete(
                nodes_url,
                headers=self._supabase._headers(),
                params={
                    "entity_type": f"eq.{et}",
                    "entity_id": f"eq.{eid}",
                },
            )
            _raise_for_status(resp, "delete_node", "DELETE", nodes_url, self._supabase)
            return True

    async def get_stats(self) -> dict[str, Any]:
        nodes = await self.list_nodes(limit=500)
        edges = await self.list_edges(limit=2000)
        node_counts = Counter(str(row.get("entity_type") or "unknown") for row in nodes)
        edge_counts = Counter(
            str(row.get("relation_type") or "unknown") for row in edges
        )
        return {
            "nodes": dict(node_counts),
            "edges": dict(edge_counts),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }


_graph_store: KnowledgeGraphStore | None = None


def get_knowledge_graph_store() -> KnowledgeGraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = KnowledgeGraphStore()
    return _graph_store
