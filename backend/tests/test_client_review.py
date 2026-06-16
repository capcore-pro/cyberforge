"""Tests Mode Client — client_reviews store et routes API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.client_review_store import ClientReviewStore


def test_create_review_generates_token_and_url() -> None:
    import asyncio

    store = ClientReviewStore()
    mock_supabase = MagicMock()
    mock_supabase.is_configured.return_value = True
    mock_supabase._rest_url.return_value = "https://example.supabase.co/rest/v1"
    mock_supabase._headers.return_value = {"apikey": "x"}
    store._supabase = mock_supabase

    created_row = {
        "id": "rev-1",
        "token": "abc123",
        "expires_at": "2026-07-01T00:00:00+00:00",
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = [created_row]

    with patch("db.client_review_store.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        with patch("db.client_review_store._raise_for_status"):
            result = asyncio.run(
                store.create_review("proj-1", "Test Client", expires_days=30)
            )

    assert result["token"] == "abc123"
    assert "/review/abc123" in result["url"]


def test_get_review_by_token_not_found() -> None:
    import asyncio

    store = ClientReviewStore()
    mock_supabase = MagicMock()
    mock_supabase.is_configured.return_value = True
    mock_supabase._rest_url.return_value = "https://example.supabase.co/rest/v1"
    mock_supabase._headers.return_value = {"apikey": "x"}
    store._supabase = mock_supabase

    mock_resp = MagicMock()
    mock_resp.json.return_value = []

    with patch("db.client_review_store.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        with patch("db.client_review_store._raise_for_status"):
            result = asyncio.run(store.get_review_by_token("missing"))

    assert result is None


def test_api_create_client_review() -> None:
    client = TestClient(create_app())
    mock_created = {
        "id": "rev-1",
        "token": "tok123",
        "url": "http://localhost:5173/review/tok123",
        "expires_at": "2026-07-01T00:00:00+00:00",
    }
    with patch(
        "api.routes.client_review.get_client_review_store"
    ) as mock_get_store:
        mock_store = MagicMock()
        mock_store.is_configured.return_value = True
        mock_store.create_review = AsyncMock(return_value=mock_created)
        mock_get_store.return_value = mock_store

        response = client.post(
            "/api/client-review/create",
            json={"project_id": "proj-1", "client_name": "Test Client"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "tok123"
    assert data["review_url"].endswith("/review/tok123")


def test_api_get_invalid_token_returns_404() -> None:
    client = TestClient(create_app())
    with patch(
        "api.routes.client_review.get_client_review_store"
    ) as mock_get_store:
        mock_store = MagicMock()
        mock_store.is_configured.return_value = True
        mock_store.get_review_by_token = AsyncMock(return_value=None)
        mock_get_store.return_value = mock_store

        response = client.get("/api/client-review/token-inexistant")

    assert response.status_code == 404


def test_api_get_review_marks_viewed_and_returns_project() -> None:
    client = TestClient(create_app())
    review = {
        "project_id": "proj-1",
        "client_name": "Alice",
        "status": "pending",
        "viewed_at": None,
        "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    }
    project = SimpleNamespace(title="Site Test", demo_url="https://demo.pages.dev/x")

    with patch(
        "api.routes.client_review.get_client_review_store"
    ) as mock_get_store, patch(
        "api.routes.client_review.get_supabase_store"
    ) as mock_supabase_store:
        mock_store = MagicMock()
        mock_store.is_configured.return_value = True
        mock_store.get_review_by_token = AsyncMock(return_value=review)
        mock_store.mark_viewed = AsyncMock()
        mock_get_store.return_value = mock_store

        sb = MagicMock()
        sb.is_configured.return_value = True
        sb.get_project = AsyncMock(
            return_value=SimpleNamespace(project=project)
        )
        mock_supabase_store.return_value = sb

        response = client.get("/api/client-review/tok-valid")

    assert response.status_code == 200
    data = response.json()
    assert data["project_title"] == "Site Test"
    assert data["demo_url"] == "https://demo.pages.dev/x"
    mock_store.mark_viewed.assert_awaited_once_with("tok-valid")


def test_api_respond_approved_logs_audit() -> None:
    client = TestClient(create_app())
    updated = {
        "project_id": "proj-1",
        "client_name": "Alice",
        "status": "approved",
        "responded_at": datetime.now(UTC).isoformat(),
    }
    project = SimpleNamespace(title="Site Test", demo_url="https://demo.pages.dev/x")

    with patch(
        "api.routes.client_review.get_client_review_store"
    ) as mock_get_store, patch(
        "api.routes.client_review.get_supabase_store"
    ) as mock_supabase_store, patch(
        "api.routes.client_review.get_audit_store"
    ) as mock_audit_store, patch(
        "api.routes.client_review.notify_client_review_response",
        new=AsyncMock(return_value=True),
    ):
        mock_store = MagicMock()
        mock_store.is_configured.return_value = True
        mock_store.submit_feedback = AsyncMock(return_value=updated)
        mock_get_store.return_value = mock_store

        sb = MagicMock()
        sb.is_configured.return_value = True
        sb.get_project = AsyncMock(
            return_value=SimpleNamespace(project=project)
        )
        mock_supabase_store.return_value = sb

        audit = MagicMock()
        audit.log = AsyncMock()
        mock_audit_store.return_value = audit

        response = client.post(
            "/api/client-review/tok-valid/respond",
            json={"status": "approved", "rating": 5},
        )

    assert response.status_code == 200
    audit.log.assert_awaited_once()
    assert audit.log.await_args.args[0] == "client_approved"
