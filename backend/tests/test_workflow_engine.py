"""Tests Workflow Engine — migration, store, pipeline, API."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.generation_stream import generation_event_store
from api.main import create_app
from db.supabase_store import get_supabase_store
from db.workflow_store import get_workflow_store

WORKFLOW_TABLES = ("workflows", "workflow_steps", "workflow_executions")
SEED_WORKFLOW_IDS = (
    "vitrine_simple",
    "ecommerce",
    "reservation",
    "app_web_crm",
    "extension_navigateur",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


async def _wait_for_workflow_execution(
    generation_id: str,
    *,
    attempts: int = 20,
) -> dict | None:
    store = get_workflow_store()
    for _ in range(attempts):
        row = await store.get_execution(generation_id)
        if row and row.get("status") in ("completed", "failed"):
            return row
        await asyncio.sleep(0.4)
    return await store.get_execution(generation_id)


def test_workflow_tables_seeded() -> None:
    asyncio.run(_test_workflow_tables_seeded())


async def _test_workflow_tables_seeded() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in WORKFLOW_TABLES:
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"

    wf_store = get_workflow_store()
    workflows = await wf_store.list_workflows(status="active")
    assert len(workflows) == 5
    assert {w["workflow_id"] for w in workflows} == set(SEED_WORKFLOW_IDS)

    vitrine = await wf_store.get_workflow("vitrine_simple")
    assert vitrine is not None
    steps = await wf_store.get_steps(str(vitrine["id"]))
    assert len(steps) == 5
    assert [s["step_name"] for s in steps] == [
        "BriefAI",
        "DesignSystemAI",
        "GeneratorAI",
        "SupervisorAI",
        "DeployAI",
    ]


def test_workflow_for_project_type_ecommerce() -> None:
    asyncio.run(_test_workflow_for_project_type_ecommerce())


async def _test_workflow_for_project_type_ecommerce() -> None:
    _require_supabase()
    store = get_workflow_store()
    workflow = await store.get_workflow_for_project_type("ecommerce")
    assert workflow is not None
    assert workflow["workflow_id"] == "ecommerce"
    steps = await store.get_steps(str(workflow["id"]))
    assert len(steps) == 7
    assert steps[0]["agent_id"] == "brief"
    assert steps[-1]["agent_id"] == "deploy"


def test_pipeline_creates_workflow_execution() -> None:
    asyncio.run(_test_pipeline_creates_workflow_execution())


async def _test_pipeline_creates_workflow_execution() -> None:
    _require_supabase()
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-wf-{uuid.uuid4().hex[:10]}"
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
                "client_name": "Workflow Test",
                "project_type": "vitrine_next",
                "description": "Test vitrine workflow",
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
            PipelineRequest(prompt="Client vitrine workflow test.", project_type="vitrine_next"),
            generation_id=gid,
        )

    assert result["success"] is True
    execution = await _wait_for_workflow_execution(gid)
    assert execution is not None
    assert execution["status"] == "completed"
    assert int(execution.get("completed_steps") or 0) == int(execution.get("total_steps") or 0)
    assert int(execution.get("total_steps") or 0) == 5
    await generation_event_store.cleanup(gid)


def test_workflows_api_list() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/workflows")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 5
    for item in data["items"]:
        assert "steps" in item
        assert item["step_count"] >= 3


def test_pipeline_graceful_degradation_without_workflow() -> None:
    asyncio.run(_test_pipeline_graceful_degradation_without_workflow())


async def _test_pipeline_graceful_degradation_without_workflow() -> None:
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-wf-fallback-{uuid.uuid4().hex[:8]}"
    await generation_event_store.create(gid)
    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"

    mock_store = MagicMock()
    mock_store.is_configured.return_value = False
    mock_store.get_workflow_for_project_type = AsyncMock(return_value=None)

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("db.workflow_store.get_workflow_store", return_value=mock_store),
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Fallback",
                "project_type": "vitrine_next",
                "description": "Test fallback",
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
            PipelineRequest(prompt="Fallback workflow test.", project_type="vitrine_next"),
            generation_id=gid,
        )

    assert result["success"] is True
    await generation_event_store.cleanup(gid)
