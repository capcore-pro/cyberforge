"""Tests Volume 06 — deployments, environment, latence API."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from config import get_settings
from db.deployment_store import DeploymentStore, get_deployment_store, reset_deployment_store
from db.supabase_store import get_supabase_store

DEPLOYMENTS_TABLE = "deployments"


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_deployments_table_exists() -> None:
    asyncio.run(_test_deployments_table_exists())


async def _test_deployments_table_exists() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{url}/{DEPLOYMENTS_TABLE}",
            headers=headers,
            params={"limit": "0"},
        )
        assert resp.status_code == 200


def test_deployment_store_record_and_update() -> None:
    asyncio.run(_test_deployment_store_record_and_update())


async def _test_deployment_store_record_and_update() -> None:
    _require_supabase()
    reset_deployment_store()
    store = get_deployment_store()
    generation_id = f"test-deploy-{int(asyncio.get_event_loop().time())}"

    row = await store.record_and_update(
        generation_id=generation_id,
        deployment_name="Test Client",
        url="https://demo.cyberforge.test/site",
        duration_ms=1234,
        status="successful",
    )
    assert row is not None
    assert row.get("status") == "successful"
    assert row.get("url") == "https://demo.cyberforge.test/site"
    assert row.get("deployed_at") is not None

    listed = await store.list_recent(limit=5)
    assert any(item.get("generation_id") == generation_id for item in listed)


def test_health_includes_environment() -> None:
    client = TestClient(create_app())
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "environment" in data
    assert data["environment"] == "development"
    settings = get_settings()
    assert settings.is_production is False
    assert settings.is_development is True


def test_latency_middleware_header() -> None:
    client = TestClient(create_app())
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "X-Response-Time" in res.headers
    assert res.headers["X-Response-Time"].endswith("ms")


def test_monitoring_health_includes_api_latency() -> None:
    client = TestClient(create_app())
    res = client.get("/api/monitoring/health")
    assert res.status_code == 200
    data = res.json()
    assert "api_latency_ms" in data
    assert isinstance(data["api_latency_ms"], int)


def test_deployment_store_record_update_unit() -> None:
    asyncio.run(_test_deployment_store_record_update_unit())


async def _test_deployment_store_record_update_unit() -> None:
    mock_supabase = MagicMock()
    mock_supabase.is_configured.return_value = True
    mock_supabase._rest_url.return_value = "https://example.supabase.co/rest/v1"
    mock_supabase._headers.return_value = {"apikey": "test"}

    store = DeploymentStore(supabase=mock_supabase)

    record_resp = MagicMock()
    record_resp.status_code = 201
    record_resp.json.return_value = [{"id": "dep-1", "status": "pending"}]

    update_resp = MagicMock()
    update_resp.status_code = 200
    update_resp.json.return_value = [
        {
            "id": "dep-1",
            "status": "successful",
            "url": "https://demo.test",
            "deployed_at": "2026-06-10T12:00:00",
        }
    ]

    with patch("db.deployment_store.httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post = AsyncMock(return_value=record_resp)
        client.patch = AsyncMock(return_value=update_resp)
        client_cls.return_value = client

        row = await store.record_and_update(
            generation_id="gen-1",
            deployment_name="Client",
            url="https://demo.test",
            duration_ms=500,
            status="successful",
        )

    assert row is not None
    assert row["status"] == "successful"
    assert row["deployed_at"] is not None
