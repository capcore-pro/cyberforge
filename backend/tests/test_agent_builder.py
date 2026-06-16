"""Tests Agent Builder — CRUD custom_agents + chat SSE."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import create_app


def test_list_custom_agents_returns_items() -> None:
    client = TestClient(create_app())
    with patch("api.routes.agent_builder.get_custom_agent_store") as mock_get:
        store = MagicMock()
        store.is_configured.return_value = True
        store.list_agents = AsyncMock(
            return_value=[
                {
                    "id": "a1",
                    "name": "Agent Test",
                    "description": "desc",
                    "system_prompt": "Tu es utile.",
                    "model": "claude-sonnet-4-6",
                    "temperature": 0.7,
                    "max_tokens": 1200,
                    "tools": ["web_search"],
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        )
        mock_get.return_value = store
        res = client.get("/api/agents/custom")
    assert res.status_code == 200
    payload = res.json()
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "a1"


def test_create_custom_agent() -> None:
    client = TestClient(create_app())
    with patch("api.routes.agent_builder.get_custom_agent_store") as mock_get:
        store = MagicMock()
        store.is_configured.return_value = True
        store.create_agent = AsyncMock(
            return_value={
                "id": "a1",
                "name": "Agent Test",
                "description": "desc",
                "system_prompt": "Tu es utile.",
                "model": "claude-sonnet-4-6",
                "temperature": 0.7,
                "max_tokens": 1200,
                "tools": ["web_search"],
                "is_active": True,
                "created_at": None,
                "updated_at": None,
            }
        )
        mock_get.return_value = store
        res = client.post(
            "/api/agents/custom",
            json={
                "name": "Agent Test",
                "description": "desc",
                "system_prompt": "Tu es utile.",
                "model": "claude-sonnet-4-6",
                "temperature": 0.7,
                "max_tokens": 1200,
                "tools": ["web_search"],
                "is_active": True,
            },
        )
    assert res.status_code == 200
    assert res.json()["id"] == "a1"


def test_chat_custom_agent_streams_sse() -> None:
    client = TestClient(create_app())

    async def fake_route(_req, task_type="content"):
        _ = task_type
        r = MagicMock()
        r.content = "Bonjour"
        r.provider = "anthropic"
        r.model = "claude-sonnet-4-6"
        r.input_tokens = 10
        r.output_tokens = 5
        r.total_tokens = 15
        return r

    with (
        patch("api.routes.agent_builder.get_custom_agent_store") as mock_get,
        patch("api.routes.agent_builder.get_llm_router") as mock_router_factory,
    ):
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_agent = AsyncMock(
            return_value={
                "id": "a1",
                "name": "Agent Test",
                "description": "desc",
                "system_prompt": "Tu es utile.",
                "model": "claude-sonnet-4-6",
                "temperature": 0.7,
                "max_tokens": 800,
                "tools": [],
                "is_active": True,
            }
        )
        mock_get.return_value = store

        router = MagicMock()
        router.route = AsyncMock(side_effect=fake_route)
        mock_router_factory.return_value = router

        res = client.post(
            "/api/agents/custom/a1/chat",
            json={"message": "Salut", "history": []},
            headers={"Accept": "text/event-stream"},
        )

    assert res.status_code == 200
    body = res.text
    assert "event: chunk" in body
    assert "event: done" in body
    assert "Bonjour" in body

