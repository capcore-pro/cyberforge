"""Tests architecture template-first."""

from __future__ import annotations

import asyncio

import pytest

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.coremind_agent import ProjectType
from agents.template_first_service import (
    must_use_template_first,
    resolve_template_definition,
)
from core.agent_contract import AgentContractError
from core.template_registry import get_template, require_template_for_plan
from core.template_engine import render_template


def _plan(template: str = "landing") -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        template=template,
        template_label="Landing",
        rationale="Test",
        complexity_score=4,
        complexity_label="Moyenne",
        market_price_min=1000,
        market_price_max=3000,
        suggested_price_min=400,
        suggested_price_max=1200,
        palette=ToolboxPalette(primary="#111", secondary="#222", accent="#333"),
    )


def test_catalog_has_landing_vitrine() -> None:
    t = get_template("landing")
    assert t is not None
    assert t.render_kind == "vitrine_shell"


def test_require_template_rejects_unknown() -> None:
    with pytest.raises(AgentContractError) as exc:
        require_template_for_plan(
            template_id="unknown_xyz",
            project_type="site_web",
            generation_mode="client_demo",
        )
    assert exc.value.code == "unknown_template"


def test_must_use_template_first_client_demo() -> None:
    assert must_use_template_first(_plan(), generation_mode="client_demo") is True


def test_must_not_template_first_real_app() -> None:
    assert must_use_template_first(_plan(), generation_mode="real_app") is False


def test_resolve_vitrine_forces_landing() -> None:
    p = _plan(template="taskflow")
    d = resolve_template_definition(p, generation_mode="client_demo")
    assert d.id == "landing"


def test_render_vitrine_template_success() -> None:
    plan = _plan()
    definition = resolve_template_definition(plan, generation_mode="client_demo")

    async def _run():
        return await render_template(
            definition,
            plan=plan,
            user_prompt="Site pour Aux Délices boulangerie à Rouen",
            research_brief={
                "nom_entreprise": "Aux Délices",
                "secteur": "commerce",
                "ville": "Rouen",
                "mots_cles": ["pain", "viennoiserie"],
            },
        )

    result = asyncio.run(_run())
    assert result.ok, result.error
    generation, preview = result.data  # type: ignore[misc]
    assert "<!DOCTYPE html>" in preview
    assert "Aux Délices" in preview
    assert "cf-vitrine-hero" in preview
    assert generation.provider == "template_first"
