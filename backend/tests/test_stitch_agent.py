"""Tests StitchAI — prompts et formatage."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.coremind_agent import ProjectType
from agents.stitch_ai import (
    build_screen_prompts,
    format_stitch_mockups_for_prompt,
    resolve_stitch_project_type,
    StitchMockup,
    StitchResult,
)


def _plan() -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        template="taskflow",
        template_label="TaskFlow",
        rationale="Test",
        complexity_score=5,
        complexity_label="Moyenne",
        market_price_min=1000,
        market_price_max=3000,
        suggested_price_min=400,
        suggested_price_max=1200,
        palette=ToolboxPalette(
            primary="#111827",
            secondary="#374151",
            accent="#d97706",
        ),
    )


def test_resolve_project_type_vitrine() -> None:
    assert (
        resolve_stitch_project_type(generation_mode="vitrine_next", plan=_plan())
        == "vitrine_next"
    )


def test_build_screen_prompts_count() -> None:
    screens = build_screen_prompts(
        project_type="ecommerce",
        sector="mode",
        client_name="Boutique Demo",
        palette={"primary": "#111", "secondary": "#222", "accent": "#333"},
        sections=["hero", "shop"],
        research_content={"mots_cles": ["mode", "paris"]},
    )
    assert len(screens) == 3
    assert "Boutique Demo" in screens[0]["prompt"]


def test_format_stitch_mockups() -> None:
    result = StitchResult(
        success=True,
        mockups=[
            StitchMockup(
                name="Accueil",
                html_url="https://example.com/a.html",
                image_url="https://example.com/a.png",
            ),
        ],
    )
    block = format_stitch_mockups_for_prompt(result)
    assert "Maquettes StitchAI" in block
    assert "Accueil" in block
