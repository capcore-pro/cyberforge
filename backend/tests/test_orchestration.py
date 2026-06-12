"""Tests Multi-Agent Orchestration Volume 04C."""

from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from agents.parallel_executor import parallel_executor
from api.generation_stream import generation_event_store
from api.main import create_app
from db.orchestration_store import get_orchestration_store
from db.supabase_store import get_supabase_store

ORCHESTRATION_TABLES = (
    "agent_sessions",
    "shared_contexts",
    "agent_messages",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


async def _wait_for_orchestration_session(
    generation_id: str,
    *,
    attempts: int = 25,
) -> dict | None:
    store = get_orchestration_store()
    for _ in range(attempts):
        row = await store.get_session(generation_id)
        if row and row.get("status") in ("completed", "failed"):
            return row
        await asyncio.sleep(0.4)
    return await store.get_session(generation_id)


def test_orchestration_tables_exist() -> None:
    asyncio.run(_test_orchestration_tables_exist())


async def _test_orchestration_tables_exist() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in ORCHESTRATION_TABLES:
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"


def test_parallel_executor_partial_failure() -> None:
    asyncio.run(_test_parallel_executor_partial_failure())


async def _test_parallel_executor_partial_failure() -> None:
    async def _success() -> str:
        return "ok"

    async def _fail() -> str:
        raise RuntimeError("boom")

    result = await parallel_executor.run_parallel(
        {
            "task_a": _success(),
            "task_b": _fail(),
        }
    )
    assert result["task_a"] == "ok"
    assert result["task_b"] is None


def test_pipeline_creates_orchestration_session() -> None:
    asyncio.run(_test_pipeline_creates_orchestration_session())


async def _test_pipeline_creates_orchestration_session() -> None:
    _require_supabase()
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-orch-{uuid.uuid4().hex[:10]}"
    await generation_event_store.create(gid)
    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Orchestration Test",
                "project_type": "vitrine_next",
                "description": "Test vitrine orchestration session.",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.cyberforge.test/site",
            "tok",
            "pass",
            "https://demo.cyberforge.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.cyberforge.test/site",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        result = await run_pipeline(
            PipelineRequest(
                prompt="Client vitrine orchestration test.",
                project_type="vitrine_next",
            ),
            generation_id=gid,
        )

    assert result["success"] is True
    session = await _wait_for_orchestration_session(gid)
    assert session is not None
    assert session["status"] == "completed"
    assert session["generation_id"] == gid
    completed = session.get("agents_completed") or []
    assert "brief" in completed
    assert "design_system" in completed
    assert "generator" in completed
    assert "supervisor" in completed
    assert "deploy" in completed
    await generation_event_store.cleanup(gid)


def test_parallel_knowledge_memory_faster_than_sequential() -> None:
    asyncio.run(_test_parallel_knowledge_memory_faster_than_sequential())


async def _test_parallel_knowledge_memory_faster_than_sequential() -> None:
    delay = 0.12

    async def _slow_knowledge() -> str:
        await asyncio.sleep(delay)
        return "knowledge-ctx"

    async def _slow_memory() -> str:
        await asyncio.sleep(delay)
        return "memory-ctx"

    t0 = time.perf_counter()
    await parallel_executor.run_parallel(
        {"knowledge": _slow_knowledge(), "memory": _slow_memory()}
    )
    parallel_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    await _slow_knowledge()
    await _slow_memory()
    sequential_ms = (time.perf_counter() - t1) * 1000

    assert parallel_ms <= max(delay * 1000 * 1.5, sequential_ms * 0.75)
    assert parallel_ms < sequential_ms


def test_orchestration_sessions_api() -> None:
    asyncio.run(_test_orchestration_sessions_api())


async def _test_orchestration_sessions_api() -> None:
    _require_supabase()
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-orch-api-{uuid.uuid4().hex[:8]}"
    await generation_event_store.create(gid)
    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "API Orch",
                "project_type": "vitrine_next",
                "description": "Test API orchestration.",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.cyberforge.test/site",
            "tok",
            "pass",
            "https://demo.cyberforge.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.cyberforge.test/site",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        await run_pipeline(
            PipelineRequest(prompt="API orchestration test.", project_type="vitrine_next"),
            generation_id=gid,
        )

    await _wait_for_orchestration_session(gid)

    with TestClient(create_app()) as client:
        res = client.get("/api/orchestration/sessions")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] >= 1
        ids = [item.get("generation_id") for item in data["items"]]
        assert gid in ids

        detail = client.get(f"/api/orchestration/sessions/{gid}")
        assert detail.status_code == 200
        detail_data = detail.json()
        assert detail_data["generation_id"] == gid
        assert "shared_contexts" in detail_data

    await generation_event_store.cleanup(gid)
