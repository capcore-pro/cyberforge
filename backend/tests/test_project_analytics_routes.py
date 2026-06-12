"""Filtres project_id sur routes analytics projet (orchestration + audit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_orchestration_sessions_filters_by_project_id(client: TestClient) -> None:
    mock_store = MagicMock()
    mock_store.is_configured.return_value = True
    mock_store.list_sessions = AsyncMock(
        return_value=[
            {
                "generation_id": "gen-1",
                "project_id": "proj-abc",
                "workflow_id": "wf-1",
                "status": "completed",
                "agents_completed": ["brief"],
                "total_agents": 4,
                "created_at": "2026-06-10T10:00:00Z",
            }
        ]
    )

    with patch(
        "api.routes.orchestration.get_orchestration_store",
        return_value=mock_store,
    ):
        res = client.get("/api/orchestration/sessions?project_id=proj-abc&limit=10")

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 1
    mock_store.list_sessions.assert_awaited_once_with(
        project_id="proj-abc",
        status=None,
        limit=10,
    )


def test_audit_events_filters_by_project_id(client: TestClient) -> None:
    mock_store = MagicMock()
    mock_store.is_configured.return_value = True
    mock_store.list_events = AsyncMock(
        return_value=[
            {
                "event_type": "project_generated",
                "project_id": "proj-abc",
                "actor_type": "system",
                "event_data": {"generation_id": "gen-1"},
                "created_at": "2026-06-10T10:00:00Z",
            }
        ]
    )

    with patch("api.routes.audit.get_audit_store", return_value=mock_store):
        res = client.get("/api/audit/events?project_id=proj-abc&limit=20")

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 1
    assert data["items"][0]["event_type"] == "project_generated"
    mock_store.list_events.assert_awaited_once_with(
        event_type=None,
        project_id="proj-abc",
        limit=20,
    )
