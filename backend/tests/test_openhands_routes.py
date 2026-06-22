"""Tests routes OpenHands Debug."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_openhands_debug_not_configured(client: TestClient) -> None:
    with patch("api.routes.openhands.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = False
        store.connection_diagnostics.return_value = {}
        mock_store.return_value = store
        res = client.post(
            "/api/openhands/debug",
            json={"project_id": "proj-1", "project_type": "website"},
        )
    assert res.status_code == 503


def test_openhands_debug_ok(client: TestClient) -> None:
    with (
        patch("api.routes.openhands.get_supabase_store") as mock_store,
        patch("api.routes.openhands.run_debug_pipeline", new_callable=AsyncMock) as mock_pipeline,
        patch("api.routes.openhands.get_audit_store") as mock_audit,
        patch("api.routes.openhands.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
    ):
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": "<html><head></head><body></body></html>",
                "project_title": "Test",
                "project_type": "site_web",
            }
        )
        store.save_editor_html = AsyncMock()
        store.save_openhands_correction = AsyncMock(return_value={"id": "oh-1"})
        store.update_project_demo_url = AsyncMock()
        mock_store.return_value = store

        mock_pipeline.return_value = {
            "corrected_code": "<!DOCTYPE html><html><head></head><body></body></html>",
            "report": {
                "issues": ["DOCTYPE manquant"],
                "corrections": ["DOCTYPE html ajouté"],
                "quality_score_final": 90,
                "iterations": 1,
            },
            "status": "done",
            "iterations": 1,
        }

        audit = MagicMock()
        audit.log = AsyncMock()
        mock_audit.return_value = audit

        mock_deploy.return_value = ("https://demo.test", "tok", "pwd", "https://demo.test")

        res = client.post(
            "/api/openhands/debug",
            json={
                "project_id": "proj-1",
                "project_type": "site_web",
                "redeploy_after": True,
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["iterations"] == 1
    assert body["redeployed"] is True
    assert body["deploy_url"] == "https://demo.test"
    store.save_editor_html.assert_awaited_once()
    store.save_openhands_correction.assert_awaited_once()
