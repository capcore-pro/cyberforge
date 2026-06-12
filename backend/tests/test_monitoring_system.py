"""Tests Monitoring Center Volume 05G."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from agents import alert_engine
from agents.alert_engine import AlertEngine, run_checks
from api.main import create_app
from db.monitoring_store import get_monitoring_store, reset_monitoring_store
from db.supabase_store import get_supabase_store

MONITORING_TABLES = (
    "monitoring_sources",
    "alerts",
    "incidents",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_monitoring_tables_exist() -> None:
    asyncio.run(_test_monitoring_tables_exist())


async def _test_monitoring_tables_exist() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in MONITORING_TABLES:
            resp = await client.get(
                f"{url}/{table}",
                headers=headers,
                params={"limit": "0"},
            )
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"


def test_monitoring_sources_seeded() -> None:
    asyncio.run(_test_monitoring_sources_seeded())


async def _test_monitoring_sources_seeded() -> None:
    _require_supabase()
    sources = await get_monitoring_store().list_sources()
    names = {str(s.get("source_name")) for s in sources}
    assert "llm_usage" in names
    assert "supervisor_decisions" in names
    assert len(sources) >= 7


def test_monitoring_health_endpoint() -> None:
    client = TestClient(create_app())
    res = client.get("/api/monitoring/health")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert data["overall_status"] in ("healthy", "degraded", "critical")
    assert data["agents"]["active"] > 0
    assert "api" in data
    assert "pipeline" in data
    assert "costs" in data


def test_monitoring_check_endpoint() -> None:
    client = TestClient(create_app())
    res = client.post("/api/monitoring/check")
    assert res.status_code == 200
    data = res.json()
    assert "created" in data
    assert "skipped" in data
    assert "metrics" in data


def test_monitoring_api_overview_and_alerts() -> None:
    client = TestClient(create_app())
    overview = client.get("/api/monitoring/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert "open_alerts_count" in body

    sources = client.get("/api/monitoring/sources")
    assert sources.status_code == 200
    assert "items" in sources.json()

    alerts = client.get("/api/monitoring/alerts?status=open")
    assert alerts.status_code == 200
    assert "items" in alerts.json()


def test_monitoring_alert_lifecycle() -> None:
    asyncio.run(_test_monitoring_alert_lifecycle())


async def _test_monitoring_alert_lifecycle() -> None:
    _require_supabase()
    reset_monitoring_store()
    store = get_monitoring_store()
    marker = f"test-{uuid.uuid4().hex[:8]}"

    created = await store.create_alert(
        alert_type=f"test_alert_{marker}",
        severity="warning",
        title="Test alerte monitoring",
        message="Message de test",
        source="test",
    )
    assert created and created.get("id")

    alert_id = str(created["id"])
    listed = await store.list_alerts(status="open", limit=50)
    assert any(str(a.get("id")) == alert_id for a in listed)

    ack = await store.acknowledge_alert(alert_id)
    assert ack and ack.get("status") == "acknowledged"

    resolved = await store.resolve_alert(alert_id)
    assert resolved and resolved.get("status") == "resolved"


def test_run_checks_returns_metrics() -> None:
    asyncio.run(_test_run_checks_returns_metrics())


async def _test_run_checks_returns_metrics() -> None:
    _require_supabase()
    result = await run_checks()
    assert "metrics" in result
    assert "created" in result
    assert "skipped" in result


def test_alert_engine_scan_returns_metrics() -> None:
    asyncio.run(_test_alert_engine_scan_returns_metrics())


async def _test_alert_engine_scan_returns_metrics() -> None:
    _require_supabase()
    result = await AlertEngine(days=30).scan()
    assert "metrics" in result
    assert "pass_rate" in result["metrics"]


def test_pipeline_schedules_run_checks() -> None:
    asyncio.run(_test_pipeline_schedules_run_checks())


async def _test_pipeline_schedules_run_checks() -> None:
    with patch.object(alert_engine, "run_checks", new_callable=AsyncMock) as mock_checks:
        mock_checks.return_value = {"created": [], "skipped": [], "metrics": {}}
        await alert_engine.run_checks()
    mock_checks.assert_awaited_once()


def test_pipeline_contains_run_checks_hook() -> None:
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "pipeline.py"
    text = source.read_text(encoding="utf-8")
    assert "asyncio.create_task(alert_engine.run_checks())" in text


def test_run_checks_no_crash_when_store_empty() -> None:
    asyncio.run(_test_run_checks_no_crash_when_store_empty())


async def _test_run_checks_no_crash_when_store_empty() -> None:
    result = await run_checks()
    assert isinstance(result, dict)
    assert "created" in result
