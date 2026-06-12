"""Tests LLM usage extraction, pricing et pipeline."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agents.llm_usage_utils import (
    merge_usage,
    pop_agent_usage,
    usage_from_anthropic_response,
)
from llm.llm_usage_service import LLMUsageTotals
from tools.llm_pricing import compute_llm_cost_usd


def test_usage_from_anthropic_response() -> None:
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=1200, output_tokens=300))
    usage = usage_from_anthropic_response(response, "claude-sonnet-4-20250514")
    assert usage is not None
    assert usage["input_tokens"] == 1200
    assert usage["output_tokens"] == 300
    assert usage["total_tokens"] == 1500
    assert usage["provider"] == "anthropic"


def test_usage_from_anthropic_response_missing() -> None:
    assert usage_from_anthropic_response(SimpleNamespace(), "model") is None


def test_merge_usage() -> None:
    left = {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "model": "m1",
        "provider": "anthropic",
    }
    right = {
        "input_tokens": 200,
        "output_tokens": 80,
        "total_tokens": 280,
        "model": "m2",
        "provider": "anthropic",
    }
    merged = merge_usage(left, right)
    assert merged is not None
    assert merged["input_tokens"] == 300
    assert merged["output_tokens"] == 130
    assert merged["total_tokens"] == 430


def test_pop_agent_usage() -> None:
    payload, usage = pop_agent_usage(
        {"tables": [], "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "model": "m", "provider": "anthropic"}}
    )
    assert "usage" not in payload
    assert usage is not None
    assert usage["total_tokens"] == 15


def test_llm_usage_totals_accumulator() -> None:
    totals = LLMUsageTotals()
    totals.add(
        "BriefAI",
        {
            "input_tokens": 1000,
            "output_tokens": 200,
            "total_tokens": 1200,
            "model": "claude-haiku-4-5-20251001",
            "provider": "anthropic",
        },
    )
    data = totals.as_dict()
    assert data["input_tokens"] == 1000
    assert data["total_tokens"] == 1200
    assert data["estimated_cost_usd"] > 0
    assert len(data["agents"]) == 1


def test_compute_llm_cost_usd() -> None:
    cost = compute_llm_cost_usd("anthropic", "claude-sonnet-4-20250514", 1_000_000, 0)
    assert cost == 3.0


def test_pipeline_emits_usage_in_done_event() -> None:
    import asyncio

    asyncio.run(_test_pipeline_emits_usage_in_done_event())


async def _test_pipeline_emits_usage_in_done_event() -> None:
    from api.generation_stream import generation_event_store
    from pipeline import PipelineRequest, run_pipeline

    gid = "test-llm-usage"
    await generation_event_store.create(gid)

    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 5200) + "</body></html>"
    mock_usage = {
        "input_tokens": 500,
        "output_tokens": 100,
        "total_tokens": 600,
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
        patch("db.supabase_store.get_supabase_store") as store_factory,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Test Co",
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

        store = MagicMock()
        store.is_configured.return_value = False
        store_factory.return_value = store

        result = await run_pipeline(
            PipelineRequest(
                prompt="Client Test — vitrine professionnelle avec services.",
                project_type="vitrine_next",
            ),
            generation_id=gid,
        )

    assert result["success"] is True
    assert result.get("total_tokens", 0) > 0
    assert result.get("estimated_cost_usd", 0) > 0
    assert svc.record_agent.await_count >= 2

    session = generation_event_store.get_session(gid)
    assert session is not None
    done_events = [e for e in session.history if e[1] == "done"]
    assert done_events
    done_payload = done_events[0][2]
    assert done_payload.get("total_tokens", 0) > 0
    assert done_payload.get("estimated_cost_usd", 0) > 0
    await generation_event_store.cleanup(gid)
