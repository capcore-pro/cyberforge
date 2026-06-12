"""Tests Tool Framework — migration, API, wrappers, logging."""

from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.supabase_store import get_supabase_store
from db.tool_store import get_tool_store
from tools.base_tool import ToolRequest
from tools.wrappers.pexels_tool import PexelsTool

TOOL_TABLES = ("tool_registry", "tool_executions", "tool_audit_logs")
SEED_TOOL_IDS = (
    "pexels",
    "cloudflare_pages",
    "firecrawl",
    "brevo",
    "replicate",
    "anthropic_api",
    "openai_api",
    "stripe_js",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


async def _wait_for_execution(tool_id: str, action: str, *, attempts: int = 10) -> dict | None:
    store = get_tool_store()
    for _ in range(attempts):
        rows = await store.list_executions(tool_id=tool_id, days=1, limit=20)
        match = next((r for r in rows if r.get("action") == action), None)
        if match:
            return match
        await asyncio.sleep(0.3)
    return None


def test_tool_tables_exist_and_seeded() -> None:
    asyncio.run(_test_tool_tables_exist_and_seeded())


async def _test_tool_tables_exist_and_seeded() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in TOOL_TABLES:
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"

    tools = await get_tool_store().list_tools()
    assert len(tools) == 8
    assert {t["tool_id"] for t in tools} == set(SEED_TOOL_IDS)


def test_tools_registry_api() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 8
    assert len(data["items"]) == 8
    pexels = next(i for i in data["items"] if i["tool_id"] == "pexels")
    assert "is_available" in pexels
    assert isinstance(pexels["is_available"], bool)


def test_pexels_tool_wrapper_and_logging() -> None:
    asyncio.run(_test_pexels_tool_wrapper_and_logging())


async def _test_pexels_tool_wrapper_and_logging() -> None:
    _require_supabase()
    tool = PexelsTool()
    assert isinstance(tool.is_available(), bool)

    request = ToolRequest(
        action="search",
        payload={"query": "restaurant", "count": 3},
        agent_id=f"test-{uuid.uuid4().hex[:8]}",
    )
    result = await tool.run(request)
    assert isinstance(result.success, bool)
    assert result.tool_id == "pexels"
    assert result.action == "search"
    assert result.duration_ms >= 0

    logged = await _wait_for_execution("pexels", "search")
    assert logged is not None
    assert int(logged.get("duration_ms") or 0) > 0
    assert logged.get("status") in ("success", "failure")


def test_tool_execution_stats_api() -> None:
    asyncio.run(_test_tool_execution_stats_api())


async def _test_tool_execution_stats_api() -> None:
    _require_supabase()
    tool = PexelsTool()
    await tool.run(
        ToolRequest(action="search", payload={"query": "hotel", "count": 2}, agent_id="stats-test")
    )
    await _wait_for_execution("pexels", "search")

    with TestClient(create_app()) as client:
        res = client.get("/api/tools/pexels/executions")
    assert res.status_code == 200
    stats = res.json()
    assert stats["tool_id"] == "pexels"
    assert stats["total"] >= 1
    assert "success_count" in stats
    assert "failure_count" in stats
    assert "avg_duration_ms" in stats
