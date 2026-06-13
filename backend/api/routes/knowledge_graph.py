"""
Routes API — Knowledge Graph (sync, nœuds, traversal, stats).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.knowledge_graph_store import get_knowledge_graph_store
from db.supabase_store import SupabaseStoreError
from knowledge.graph_service import graph_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-graph"])


class UpsertEdgeRequest(BaseModel):
    source_type: str = Field(..., min_length=1, max_length=100)
    source_id: str = Field(..., min_length=1, max_length=255)
    target_type: str = Field(..., min_length=1, max_length=100)
    target_id: str = Field(..., min_length=1, max_length=255)
    relation_type: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(default=1.0, ge=0)
    properties: dict | None = None


@router.post("/knowledge-graph/sync")
async def sync_knowledge_graph() -> dict:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        return await graph_service.sync_from_database()
    except SupabaseStoreError as exc:
        logger.warning("sync_knowledge_graph: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/knowledge-graph/nodes")
async def list_knowledge_graph_nodes(
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        return []
    try:
        return await store.list_nodes(entity_type=entity_type, limit=limit)
    except SupabaseStoreError as exc:
        logger.warning("list_knowledge_graph_nodes: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/knowledge-graph/edges")
async def list_knowledge_graph_edges(
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[dict]:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        return []
    try:
        return await store.list_edges(limit=limit)
    except SupabaseStoreError as exc:
        logger.warning("list_knowledge_graph_edges: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/knowledge-graph/nodes/{entity_type}/{entity_id}")
async def get_knowledge_graph_node(entity_type: str, entity_id: str) -> dict:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        node = await store.get_node(entity_type, entity_id)
        if not node:
            raise HTTPException(status_code=404, detail="Nœud introuvable.")
        neighbors = await store.get_neighbors(
            entity_type,
            entity_id,
            direction="both",
        )
        return {**node, "neighbors": neighbors}
    except SupabaseStoreError as exc:
        logger.warning("get_knowledge_graph_node: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/knowledge-graph/traverse/{entity_type}/{entity_id}")
async def traverse_knowledge_graph(
    entity_type: str,
    entity_id: str,
    max_depth: int = Query(default=3, ge=1, le=10),
) -> list[dict]:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        rows = await store.traverse(entity_type, entity_id, max_depth=max_depth)
        if not rows:
            node = await store.get_node(entity_type, entity_id)
            if not node:
                raise HTTPException(status_code=404, detail="Nœud introuvable.")
        return rows
    except SupabaseStoreError as exc:
        logger.warning("traverse_knowledge_graph: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/knowledge-graph/edges")
async def upsert_knowledge_graph_edge(body: UpsertEdgeRequest) -> dict:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        return await store.upsert_edge(
            source_type=body.source_type,
            source_id=body.source_id,
            target_type=body.target_type,
            target_id=body.target_id,
            relation_type=body.relation_type,
            weight=body.weight,
            properties=body.properties,
        )
    except SupabaseStoreError as exc:
        logger.warning("upsert_knowledge_graph_edge: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/knowledge-graph/stats")
async def knowledge_graph_stats() -> dict:
    store = get_knowledge_graph_store()
    if not store.is_configured():
        return {
            "nodes": {},
            "edges": {},
            "total_nodes": 0,
            "total_edges": 0,
        }
    try:
        return await store.get_stats()
    except SupabaseStoreError as exc:
        logger.warning("knowledge_graph_stats: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
