"""Tests DesignSystemAI — familles sectorielles et loi visuelle."""

from __future__ import annotations

import asyncio
import json

from agents.architect_agent import ToolboxPalette
from agents.coremind_agent import ProjectType
from agents.design_system_ai import (
    DesignSystemJSON,
    _CONTRACT_KEYS,
    _FONT_STYLES,
    build_design_system,
    design_system_to_css_variables,
    format_design_system_for_prompt,
    resolve_visual_family,
)
from core.agent_contract import require_ok


def test_missing_client_name_fails() -> None:
    result = build_design_system(
        sector="restauration",
        client_name="",
        project_type=ProjectType.SITE_WEB,
    )
    assert not result.ok
    assert result.error and result.error.code == "missing_client_name"


def test_boulangerie_warm_palette_artisanal_fonts() -> None:
    result = build_design_system(
        sector="commerce",
        client_name="Aux Délices",
        project_type=ProjectType.SITE_WEB,
        user_prompt="Boulangerie artisanale à Rouen",
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#5C3A21"
    assert doc.colors.bg == "#FCF7F0"
    assert doc.fonts.heading == _FONT_STYLES["artisanal"][0]
    assert doc.fonts.body == _FONT_STYLES["artisanal"][1]
    assert "artisanal" in doc.style_keywords


def test_nautisme_deep_blue_moderne_fonts() -> None:
    result = build_design_system(
        sector="nautisme",
        client_name="Marine Atlantique",
        project_type=ProjectType.SITE_WEB,
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#0A3D62"
    assert doc.fonts.heading == "Inter"
    assert doc.fonts.body == "Space Grotesk"


def test_tech_dark_neon() -> None:
    result = build_design_system(
        sector="technologie",
        client_name="DataFlow",
        project_type=ProjectType.APPLICATION_WEB,
        user_prompt="SaaS digital startup",
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#0D1117"
    assert doc.colors.accent == "#58A6FF"
    assert not doc.colors.text.startswith("#1A")


def test_beaute_elegant_fonts() -> None:
    result = build_design_system(
        sector="beaute",
        client_name="Salon Éclat",
        project_type=ProjectType.SITE_WEB,
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#1A1A1A"
    assert doc.fonts.heading == "Cormorant"
    assert doc.fonts.body == "Raleway"


def test_juridique_navy_gold() -> None:
    result = build_design_system(
        sector="immobilier",
        client_name="Cabinet Mercier",
        project_type=ProjectType.SITE_WEB,
        user_prompt="Cabinet d'avocats finance",
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#1C2833"
    assert doc.colors.accent == "#C9A84C"


def test_visual_law_in_prompt() -> None:
    result = build_design_system(
        sector="artisanat",
        client_name="Menuiserie Bois",
        project_type=ProjectType.SITE_WEB,
    )
    doc = require_ok(result)
    block = format_design_system_for_prompt(doc)
    assert "LOI VISUELLE" in block
    assert "TOUS les agents" in block
    parsed = json.loads(block.split("```json\n")[1].split("\n```")[0])
    assert set(parsed.keys()) == _CONTRACT_KEYS


def test_resolve_family_from_prompt() -> None:
    assert resolve_visual_family("commerce", "boulangerie patisserie") == "alimentaire"
    assert resolve_visual_family("commerce", "startup SaaS tech") == "tech_digital"


def test_palette_preference_merges() -> None:
    pref = ToolboxPalette(primary="#FF0000", secondary="#FFFFFF", accent="#00FF00")
    result = build_design_system(
        sector="sport",
        client_name="Gym Fit",
        palette_preference=pref,
        project_type="site_web",
    )
    doc = require_ok(result)
    assert doc.colors.primary == "#FF0000"


def test_css_variables_derived() -> None:
    result = build_design_system(
        sector="sante",
        client_name="Clinique Vert",
        project_type=ProjectType.SITE_WEB,
    )
    doc = require_ok(result)
    css = design_system_to_css_variables(doc)
    assert ":root" in css
    assert doc.colors.primary in css


def test_agent_run_async() -> None:
    from agents.design_system_ai import DesignSystemAgent

    agent = DesignSystemAgent()

    async def _run():
        return await agent.generate(
            sector="restauration",
            client_name="Le Bistrot",
            project_type=ProjectType.SITE_WEB,
        )

    result = asyncio.run(_run())
    assert result.ok
    DesignSystemJSON.model_validate(result.data.to_contract_dict())  # type: ignore[union-attr]
