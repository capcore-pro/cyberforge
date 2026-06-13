"""Tests Knowledge Graph — store, service, API, pipeline."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from knowledge.graph_service import KnowledgeGraphService, _get_agents_for_type


def test_get_agents_for_type_variants() -> None:
    assert "database" in _get_agents_for_type("application_web")
    assert "payment" in _get_agents_for_type("ecommerce")
    assert _get_agents_for_type("extension_navigateur") == ["brief", "deploy"]


def test_sync_from_database_counts_nodes_and_edges() -> None:
    graph_store = MagicMock()
    graph_store.upsert_node = AsyncMock(return_value={"id": "n1"})
    graph_store.upsert_edge = AsyncMock(return_value={"id": "e1"})

    agent_store = MagicMock()
    agent_store.list_all = AsyncMock(
        return_value=[
            {
                "agent_id": "brief",
                "name": "BriefAI",
                "category": "ingestion",
                "model": "claude",
                "in_pipeline": True,
            }
        ]
    )

    workflow_store = MagicMock()
    workflow_store.list_workflows = AsyncMock(
        return_value=[
            {
                "id": "wf-uuid",
                "workflow_id": "vitrine_simple",
                "name": "Vitrine Simple",
                "project_types": ["vitrine_next"],
            }
        ]
    )
    workflow_store.get_steps = AsyncMock(
        return_value=[
            {"agent_id": "brief", "tool_id": None},
            {"agent_id": "generator", "tool_id": "deploy_tool"},
        ]
    )

    tool_store = MagicMock()
    tool_store.list_tools = AsyncMock(
        return_value=[{"tool_id": "deploy_tool", "name": "Deploy", "category": "deploy"}]
    )

    prompt_store = MagicMock()
    prompt_store.list_all = AsyncMock(
        return_value=[
            {
                "slug": "brief-system",
                "name": "Brief System",
                "agent_slug": "brief-ai",
            }
        ]
    )

    knowledge_store = MagicMock()
    knowledge_store.list_documents = AsyncMock(
        return_value=[
            {
                "id": "doc-1",
                "title": "Guide",
                "source_type": "manual",
                "project_id": "proj-1",
            }
        ]
    )

    service = KnowledgeGraphService()
    service._graph_store = graph_store
    service._agent_store = agent_store
    service._workflow_store = workflow_store
    service._tool_store = tool_store
    service._prompt_store = prompt_store
    service._knowledge_store = knowledge_store

    result = asyncio.run(service.sync_from_database())

    assert result["nodes_created"] >= 4
    assert result["edges_created"] >= 3
    assert result["status"] == "synced"


def test_add_generation_to_graph_creates_project_edges() -> None:
    graph_store = MagicMock()
    graph_store.upsert_node = AsyncMock(return_value={"id": "p1"})
    graph_store.upsert_edge = AsyncMock(return_value={"id": "e1"})

    service = KnowledgeGraphService()
    service._graph_store = graph_store

    asyncio.run(
        service.add_generation_to_graph(
            brief={"project_type": "vitrine_next", "client_name": "Acme"},
            generation_id="gen-123",
            project_id="proj-abc",
        )
    )

    graph_store.upsert_node.assert_awaited_once()
    assert graph_store.upsert_edge.await_count >= 5


def test_sync_api_route() -> None:
    graph_store = MagicMock()
    graph_store.is_configured.return_value = True

    with patch(
        "api.routes.knowledge_graph.graph_service.sync_from_database",
        new=AsyncMock(
            return_value={
                "nodes_created": 30,
                "edges_created": 35,
                "status": "synced",
            }
        ),
    ):
        with patch(
            "api.routes.knowledge_graph.get_knowledge_graph_store",
            return_value=graph_store,
        ):
            client = TestClient(create_app())
            res = client.post("/api/knowledge-graph/sync")

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["nodes_created"] >= 11
    assert data["edges_created"] >= 29


def test_traverse_api_route() -> None:
    graph_store = MagicMock()
    graph_store.is_configured.return_value = True
    graph_store.traverse = AsyncMock(
        return_value=[
            {
                "node_type": "workflow",
                "node_id": "vitrine_simple",
                "node_label": "Vitrine Simple",
                "relation": None,
                "depth": 0,
                "path": "workflow:vitrine_simple",
            },
            {
                "node_type": "agent",
                "node_id": "brief",
                "node_label": "BriefAI",
                "relation": "uses",
                "depth": 1,
                "path": "workflow:vitrine_simple → uses → agent:brief",
            },
        ]
    )
    graph_store.get_node = AsyncMock(return_value={"entity_type": "workflow"})

    with patch(
        "api.routes.knowledge_graph.get_knowledge_graph_store",
        return_value=graph_store,
    ):
        client = TestClient(create_app())
        res = client.get(
            "/api/knowledge-graph/traverse/workflow/vitrine_simple?max_depth=2"
        )

    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) >= 2
    assert any(row["node_type"] == "agent" for row in rows)


def test_stats_api_route() -> None:
    graph_store = MagicMock()
    graph_store.is_configured.return_value = True
    graph_store.get_stats = AsyncMock(
        return_value={
            "nodes": {"agent": 11, "workflow": 5},
            "edges": {"uses": 30},
            "total_nodes": 16,
            "total_edges": 30,
        }
    )

    with patch(
        "api.routes.knowledge_graph.get_knowledge_graph_store",
        return_value=graph_store,
    ):
        client = TestClient(create_app())
        res = client.get("/api/knowledge-graph/stats")

    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 16
    assert data["nodes"]["agent"] == 11
