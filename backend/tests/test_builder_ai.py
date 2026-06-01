"""Tests BuilderAI v2 — assemblage template."""

from __future__ import annotations

import asyncio

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.builder_ai import (
    assemble_vitrine_html,
    minify_html_light,
    optimize_html,
    uses_template_assembly,
    validate_html_tags,
)
from agents.coremind_agent import CoreMindAnalysis, ProjectType
from agents.design_system_ai import build_design_system
from agents.template_ai import load_sector_template_html
from core.agent_contract import require_ok


def _plan() -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        template="landing",
        template_label="Landing",
        rationale="Test",
        complexity_score=4,
        complexity_label="Moyenne",
        market_price_min=500,
        market_price_max=1500,
        suggested_price_min=200,
        suggested_price_max=600,
        palette=ToolboxPalette(primary="#5C3A21", secondary="#FCF7F0", accent="#C9A84C"),
    )


def test_uses_template_assembly_vitrine_next() -> None:
    assert uses_template_assembly(_plan(), generation_mode="vitrine_next") is True


def test_validate_and_minify() -> None:
    html = load_sector_template_html("vitrine_default.html")
    ds = require_ok(
        build_design_system(
            sector="commerce",
            client_name="Test Co",
            project_type=ProjectType.SITE_WEB,
        )
    )
    filled = require_ok(
        assemble_vitrine_html(
            template_html=html,
            client_name="Test Co",
            sector="commerce",
            city="Paris",
            design_system=ds.to_contract_dict(),
            template_id="vitrine_default",
        )
    )
    report = validate_html_tags(filled.html)
    assert report.valid
    optimized, opt_report = optimize_html(filled.html, strict=True)
    assert len(optimized) <= len(filled.html) + 50
    assert opt_report.valid


def test_assemble_no_placeholders_left() -> None:
    raw = load_sector_template_html("vitrine_alimentaire.html")

    data = require_ok(
        assemble_vitrine_html(
            template_html=raw,
            client_name="Aux Délices",
            sector="restauration",
            city="Rouen",
            research_content={"mots_cles": ["pain", "viennoiserie"]},
            template_id="vitrine_alimentaire",
            user_prompt="Boulangerie Rouen",
        )
    )
    assert "{{" not in data.html
    assert "Service 1" not in data.html
    assert data.generation.provider == "builder_assembly"


def test_builder_agent_vitrine_next_assembly() -> None:
    from agents.builder_agent import BuilderAgent, BuilderProvider
    from agents.coremind_agent import CoreMindAnalysis, ComplexityLevel, RecommendedTool

    analysis = CoreMindAnalysis(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        complexity=ComplexityLevel.MOYENNE,
        complexity_score=5,
        recommended_tool=RecommendedTool.V0,
        tool_rationale="Test",
        next_steps=["Assembler la vitrine"],
        summary="Test",
    )
    agent = BuilderAgent()

    async def _run():
        return await agent.build(
            "Boulangerie Aux Délices à Rouen",
            plan=_plan(),
            analysis=analysis,
            generation_mode="vitrine_next",
            design_system=require_ok(
                build_design_system(
                    sector="restauration",
                    client_name="Aux Délices",
                    project_type=ProjectType.SITE_WEB,
                )
            ).to_contract_dict(),
            sector_template={
                "template_id": "vitrine_alimentaire",
                "html_raw": load_sector_template_html("vitrine_alimentaire.html"),
                "sector": "restauration",
            },
        )

    result = asyncio.run(_run())
    assert not result.fallback_to_coremind
    assert result.decision.provider == BuilderProvider.ASSEMBLY
    assert result.preview_html
    assert "{{" not in result.preview_html
