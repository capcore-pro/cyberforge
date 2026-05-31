"""Tests routage OpenHands dans le pipeline."""

from __future__ import annotations

from unittest.mock import patch

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import ProjectType
from agents.openhands_agent import openhands_eligible
from agents.pipeline_graph import (
    DIRECT_COREMIND_MODES,
    PipelineState,
    _openhands_requested,
    _route_after_architect,
)


def _plan(
    *,
    complexity_score: int = 8,
    project_type: ProjectType = ProjectType.APPLICATION_WEB,
) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=project_type,
        project_type_label="Application web",
        template="crm",
        template_label="CRM",
        rationale="App complexe avec auth et dashboard.",
        complexity_score=complexity_score,
        complexity_label="Complexe",
        market_price_min=5000,
        market_price_max=12000,
        suggested_price_min=2000,
        suggested_price_max=4800,
        pricing_category="application_web",
    )


def test_openhands_eligible_real_app_high_complexity() -> None:
    plan = _plan(complexity_score=8)
    assert openhands_eligible(plan=plan, generation_mode="real_app", enabled=True)


def test_openhands_not_eligible_low_complexity() -> None:
    plan = _plan(complexity_score=5)
    assert not openhands_eligible(plan=plan, generation_mode="real_app", enabled=True)


def test_openhands_eligible_application_web_type() -> None:
    plan = _plan(complexity_score=7, project_type=ProjectType.APPLICATION_WEB)
    assert openhands_eligible(plan=plan, generation_mode="client_demo", enabled=True)


def test_route_after_architect_to_openhands() -> None:
    state: PipelineState = {
        "architect_plan": _plan(),
        "generation_mode": "real_app",
        "openhands_enabled": True,
    }
    with patch("agents.pipeline_graph.OpenHandsAgent") as mock_cls:
        mock_cls.return_value.is_configured.return_value = True
        with patch("agents.pipeline_graph.get_settings") as mock_settings:
            mock_settings.return_value.openhands_enabled = True
            mock_settings.return_value.openhands_complexity_threshold = 7
            assert _route_after_architect(state) == "openhands"


def test_route_after_architect_real_app_low_complexity_to_coremind() -> None:
    state: PipelineState = {
        "architect_plan": _plan(complexity_score=4),
        "generation_mode": "real_app",
        "openhands_enabled": True,
    }
    assert _route_after_architect(state) == "coremind"
    assert "real_app" in DIRECT_COREMIND_MODES


def test_openhands_disabled_skips_routing() -> None:
    state: PipelineState = {
        "architect_plan": _plan(),
        "generation_mode": "real_app",
        "openhands_enabled": False,
    }
    assert not _openhands_requested(state)
    assert _route_after_architect(state) == "coremind"
