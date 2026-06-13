"""Tests Volume 07 — security events, rate limiting, key validation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import RATE_LIMITS, _rate_limit_store, create_app
from db.security_store import SecurityStore, get_security_store, reset_security_store
from db.supabase_store import get_supabase_store

SECURITY_EVENTS_TABLE = "security_events"


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_security_events_table_exists() -> None:
    asyncio.run(_test_security_events_table_exists())


async def _test_security_events_table_exists() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{url}/{SECURITY_EVENTS_TABLE}",
            headers=headers,
            params={"limit": "0"},
        )
        assert resp.status_code == 200


def test_rate_limit_generate_post() -> None:
    _rate_limit_store.clear()
    client = TestClient(create_app())
    payload = {"prompt": "site vitrine test", "sync": False}
    last_status = None
    for _ in range(11):
        res = client.post("/api/generate", json=payload)
        last_status = res.status_code
    assert last_status == 429
    data = res.json()
    assert data.get("error") == "Rate limit dépassé"
    assert "Retry-After" in res.headers
    assert res.headers["Retry-After"] == str(RATE_LIMITS["/api/generate"][1])


def test_rate_limit_get_not_limited() -> None:
    _rate_limit_store.clear()
    client = TestClient(create_app())
    for _ in range(20):
        res = client.get("/api/health")
        assert res.status_code == 200


def test_secrets_save_invalid_key_warning() -> None:
    mock_vault = MagicMock()
    mock_status = MagicMock()
    mock_status.has_vault = True
    mock_status.locked = False
    mock_status.configured = {}
    mock_vault.status.return_value = mock_status

    with (
        patch("api.routes.secrets.get_secret_vault", return_value=mock_vault),
        patch("api.routes.secrets.test_api_key", return_value=(False, "Clé invalide (401)")),
        patch("api.routes.secrets.get_settings"),
        patch("api.routes.secrets.llm_provider_flags", return_value={}),
        patch("api.routes.secrets._merge_configured_flags", return_value={}),
    ):
        client = TestClient(create_app())
        res = client.post(
            "/api/secrets/save",
            json={
                "password": "test-password",
                "anthropic_api_key": "sk-invalid-key",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    assert "ANTHROPIC_API_KEY" not in data.get("saved", [])
    assert any(w.get("key") == "ANTHROPIC_API_KEY" for w in data.get("warnings", []))
    saved_secrets = mock_vault.save.call_args.kwargs.get("secrets", {})
    assert saved_secrets.get("ANTHROPIC_API_KEY") is None


def test_secrets_save_valid_key_and_event() -> None:
    asyncio.run(_test_secrets_save_valid_key_and_event())


async def _test_secrets_save_valid_key_and_event() -> None:
    _require_supabase()
    reset_security_store()
    mock_vault = MagicMock()
    mock_status = MagicMock()
    mock_status.has_vault = True
    mock_status.locked = False
    mock_status.configured = {"anthropic": True}
    mock_vault.status.return_value = mock_status
    pending_tasks: list = []

    def _capture_task(coro):
        pending_tasks.append(coro)
        return MagicMock()

    with (
        patch("api.routes.secrets.get_secret_vault", return_value=mock_vault),
        patch("api.routes.secrets.test_api_key", return_value=(True, "Connexion réussie")),
        patch("api.routes.secrets.get_settings"),
        patch("api.routes.secrets.llm_provider_flags", return_value={}),
        patch("api.routes.secrets._merge_configured_flags", return_value={"anthropic": True}),
        patch("api.routes.secrets.asyncio.create_task", side_effect=_capture_task),
    ):
        client = TestClient(create_app())
        res = client.post(
            "/api/secrets/save",
            json={
                "password": "test-password",
                "anthropic_api_key": "sk-valid-test-key",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert "ANTHROPIC_API_KEY" in data.get("saved", [])
    assert data.get("warnings") == []

    for coro in pending_tasks:
        await coro

    events = await get_security_store().list_events(
        event_type="api_key_changed", limit=5
    )
    assert any("ANTHROPIC_API_KEY" in str(e.get("description", "")) for e in events)


def test_monitoring_security_endpoints() -> None:
    asyncio.run(_test_monitoring_security_endpoints())


async def _test_monitoring_security_endpoints() -> None:
    _require_supabase()
    reset_security_store()
    store = get_security_store()
    await store.log_event(
        event_type="api_key_changed",
        severity="low",
        source="test",
        description="Clé TEST_KEY modifiée",
    )

    client = TestClient(create_app())
    events_res = client.get("/api/monitoring/security-events")
    assert events_res.status_code == 200
    events_data = events_res.json()
    assert "items" in events_data
    assert events_data["count"] >= 1

    stats_res = client.get("/api/monitoring/security-stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total" in stats
    assert "by_severity" in stats
    assert "by_type" in stats
    assert stats["by_severity"].get("low", 0) >= 1


def test_security_store_get_stats_unit() -> None:
    asyncio.run(_test_security_store_get_stats_unit())


async def _test_security_store_get_stats_unit() -> None:
    mock_supabase = MagicMock()
    mock_supabase.is_configured.return_value = True
    mock_supabase._rest_url.return_value = "https://example.supabase.co/rest/v1"
    mock_supabase._headers.return_value = {"apikey": "test"}

    list_resp = MagicMock()
    list_resp.status_code = 200
    list_resp.json.return_value = [
        {"event_type": "api_key_changed", "severity": "low", "resolved": False},
        {"event_type": "generation_failed_repeatedly", "severity": "medium", "resolved": True},
    ]

    store = SecurityStore(supabase=mock_supabase)
    with patch("db.security_store.httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.get = AsyncMock(return_value=list_resp)
        client_cls.return_value = client

        stats = await store.get_stats()

    assert stats["total"] == 2
    assert stats["by_severity"]["low"] == 1
    assert stats["by_severity"]["medium"] == 1
    assert stats["by_type"]["api_key_changed"] == 1
    assert stats["unresolved"] == 1
