"""Tests Volume 3 — migration, audit pipeline, prompts, agent executions."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.agent_execution_store import get_agent_execution_store
from db.audit_store import get_audit_store
from db.prompt_store import get_prompt_store
from db.supabase_store import get_supabase_store
from llm.llm_usage_service import LLMUsageTotals

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = REPO_ROOT / "backend" / "scripts" / "seed_prompts.py"

VOLUME3_TABLES = (
    "agent_executions",
    "audit_logs",
    "prompt_categories",
    "prompts",
    "prompt_versions",
    "templates",
    "template_versions",
    "roles",
    "permissions",
    "role_permissions",
)

SEED_SLUGS = (
    "brief-ai-system",
    "generator-ai-system",
    "supervisor-validation-rules",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_volume3_tables_exist() -> None:
    asyncio.run(_test_volume3_tables_exist())


async def _test_volume3_tables_exist() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in VOLUME3_TABLES:
            resp = await client.get(
                f"{url}/{table}",
                headers=headers,
                params={"limit": "0"},
            )
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"


def test_pipeline_audit_project_generated() -> None:
    asyncio.run(_test_pipeline_audit_project_generated())


async def _test_pipeline_audit_project_generated() -> None:
    _require_supabase()
    from api.generation_stream import generation_event_store
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-audit-{uuid.uuid4().hex[:8]}"
    await generation_event_store.create(gid)
    marker = f"audit-marker-{uuid.uuid4().hex[:8]}"

    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 5200) + "</body></html>"
    mock_usage = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "model": "claude-sonnet-4-20250514",
        "provider": "anthropic",
    }

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("pipeline.get_llm_usage_service") as svc_factory,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": marker,
                "project_type": "vitrine_next",
                "sector": "commerce test",
                "description": "Description test suffisamment longue pour valider le brief client.",
                "services": ["Service A", "Service B", "Service C"],
                "usage": mock_usage,
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html, "usage": mock_usage}
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
                "unlock_url": "https://demo.cyberforge.test/unlock",
                "demo_token": "tok",
                "demo_password": "pass",
            }
        )

        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        async def _record_agent(
            agent_name: str,
            usage: dict | None,
            *,
            totals: LLMUsageTotals | None = None,
            **_: object,
        ) -> None:
            if totals is not None:
                totals.add(agent_name, usage)

        svc = MagicMock()
        svc.record_agent = AsyncMock(side_effect=_record_agent)
        svc.finalize_generation = AsyncMock()
        svc_factory.return_value = svc

        result = await run_pipeline(
            PipelineRequest(
                prompt=f"{marker} — vitrine professionnelle avec services.",
                project_type="vitrine_next",
            ),
            generation_id=gid,
        )

    assert result["success"] is True
    await asyncio.sleep(0.5)

    events = await get_audit_store().list_events(event_type="project_generated", limit=20)
    matching = [
        e
        for e in events
        if isinstance(e.get("event_data"), dict)
        and e["event_data"].get("client_name") == marker
    ]
    assert matching, "Aucun événement project_generated avec le marqueur attendu"
    await generation_event_store.cleanup(gid)


def test_prompt_store_api_create() -> None:
    _require_supabase()
    slug = f"test-prompt-{uuid.uuid4().hex[:8]}"
    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/prompts-library",
        json={
            "name": "Test",
            "slug": slug,
            "content": "Tu es un agent test",
            "category_slug": "system",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("slug") == slug
    assert data.get("id")

    async def _check() -> None:
        row = await get_prompt_store().get_by_slug(slug)
        assert row is not None
        assert row.get("content") == "Tu es un agent test"

    asyncio.run(_check())


def test_agent_execution_store_record() -> None:
    asyncio.run(_test_agent_execution_store_record())


async def _test_agent_execution_store_record() -> None:
    _require_supabase()
    store = get_agent_execution_store()
    row = await store.record(
        agent_name="BriefAI",
        execution_type="generation",
        status="success",
        input_tokens=500,
        output_tokens=200,
        duration_ms=1200,
    )
    assert row.get("id")
    assert row.get("agent_name") == "BriefAI"
    assert row.get("total_tokens") == 700
    assert row.get("status") == "success"


def test_seed_prompts_script() -> None:
    _require_supabase()
    proc = subprocess.run(
        [sys.executable, str(SEED_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    async def _check() -> None:
        store = get_prompt_store()
        for slug in SEED_SLUGS:
            row = await store.get_by_slug(slug)
            assert row is not None, f"Prompt seed manquant: {slug}"

    asyncio.run(_check())
