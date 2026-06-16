"""Tests routes éditeur inline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_get_editor_html_not_configured(client: TestClient) -> None:
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = False
        store.connection_diagnostics.return_value = {}
        mock_store.return_value = store
        res = client.get("/api/editor/proj-1/html")
    assert res.status_code == 503


def test_get_editor_html_ok(client: TestClient) -> None:
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": "<!DOCTYPE html><html><body><h1>Hi</h1></body></html>",
                "demo_url": "https://demo.test",
                "project_title": "Test",
            }
        )
        mock_store.return_value = store
        res = client.get("/api/editor/proj-1/html")
    assert res.status_code == 200
    body = res.json()
    assert body["generation_id"] == "gen-1"
    assert "Hi" in body["html"]
    assert body["demo_url"] == "https://demo.test"


def test_patch_editor_html_ok(client: TestClient) -> None:
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={"html": "<html></html>", "generation_id": "gen-1"}
        )
        store.save_editor_html = AsyncMock()
        mock_store.return_value = store
        res = client.patch(
            "/api/editor/proj-1/html",
            json={"generation_id": "gen-1", "html": "<html><body>ok</body></html>"},
        )
    assert res.status_code == 200
    assert res.json()["saved"] is True
