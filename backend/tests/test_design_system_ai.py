"""Tests DesignSystemAI — familles visuelles et tokens CSS."""

from __future__ import annotations

import asyncio

from agents.design_system_ai import (
    STYLE_FAMILIES,
    DesignSystemAgent,
    build_design_system,
    design_system_to_css_variables,
    format_design_system_for_prompt,
    inject_design_system_into_html,
    is_valid_design_system,
    resolve_visual_family,
)


def test_vitrine_boulangerie_premium_light() -> None:
    brief = {
        "project_type": "vitrine_next",
        "sector": "boulangerie",
        "couleur_primaire": "#5C3A21",
        "couleur_secondaire": "#FCF7F0",
    }
    ds = build_design_system(brief)
    assert ds["style_family"] == "premium_light"
    assert ds["colors"]["primary"] == "#5C3A21"
    assert ds["colors"]["background"] == STYLE_FAMILIES["premium_light"]["bg"]
    assert ds["fonts"]["heading"] == "Playfair Display"
    assert is_valid_design_system(ds)


def test_ecommerce_mode_premium_commerce() -> None:
    brief = {
        "project_type": "ecommerce",
        "sector": "mode",
        "couleur_primaire": "#d4a843",
    }
    ds = build_design_system(brief)
    assert ds["style_family"] == "premium_commerce"
    assert ds["colors"]["primary"] == "#d4a843"
    assert ds["fonts"]["heading"] == "Inter"
    assert ds["fonts"]["body"] == "Inter"


def test_application_web_premium_dark() -> None:
    brief = {
        "project_type": "application_web",
        "sector": "dashboard-analytics",
        "couleur_primaire": "#6366f1",
    }
    ds = build_design_system(brief)
    assert ds["style_family"] == "premium_dark"
    assert ds["colors"]["primary"] == "#6366f1"
    assert ds["colors"]["background"] == "#0f1117"


def test_sector_suggests_primary_when_missing() -> None:
    ds = build_design_system(
        {"project_type": "vitrine_next", "sector": "nautisme marine", "client_name": "Marine"}
    )
    assert ds["colors"]["primary"] == "#0A3D62"


def test_derived_colors_and_css_variables() -> None:
    ds = build_design_system(
        {"project_type": "vitrine_next", "couleur_primaire": "#5C3A21"}
    )
    assert ds["colors"]["accent"] != ds["colors"]["primary"]
    assert ds["colors"]["primary_dark"] != ds["colors"]["primary"]
    assert "rgba" in ds["colors"]["overlay"]
    css = design_system_to_css_variables(ds)
    assert ":root" in css
    assert "--color-primary: #5C3A21" in css
    assert "--font-heading" in css
    assert "cf-design-system" in css


def test_format_design_system_for_prompt() -> None:
    ds = build_design_system(
        {"project_type": "site_reservation", "sector": "camping", "couleur_primaire": "#16a34a"}
    )
    block = format_design_system_for_prompt(ds)
    assert "## design_system" in block
    assert "Famille : nature_warm" in block
    assert ":root" in block
    assert "Règles d'application" in block


def test_inject_design_system_into_html() -> None:
    ds = build_design_system({"project_type": "vitrine_next", "couleur_primaire": "#5C3A21"})
    html = "<html><head><style>body{margin:0}</style></head><body></body></html>"
    out = inject_design_system_into_html(html, ds)
    assert "--color-primary" in out
    assert "--font-heading" in out
    assert inject_design_system_into_html(out, ds) == out


def test_resolve_visual_family_legacy() -> None:
    assert resolve_visual_family("commerce", "boulangerie patisserie") == "alimentaire"
    assert resolve_visual_family("commerce", "startup SaaS tech") == "tech_digital"


def test_design_system_agent_run() -> None:
    agent = DesignSystemAgent()
    ds = agent.run(
        {
            "project_type": "extension_navigateur",
            "couleur_primaire": "#6366f1",
        }
    )
    assert ds["style_family"] == "compact_dark"
    assert is_valid_design_system(ds)


def test_agent_generate_async_legacy() -> None:
    agent = DesignSystemAgent()

    async def _run():
        return await agent.generate(
            sector="restauration",
            client_name="Le Bistrot",
            project_type="vitrine_next",
        )

    result = asyncio.run(_run())
    assert result.ok
    data = result.data.to_contract_dict()  # type: ignore[union-attr]
    assert is_valid_design_system(data)
