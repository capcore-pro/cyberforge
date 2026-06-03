"""BuilderAI — force template ecommerce et nettoyage markdown."""

from __future__ import annotations

import asyncio

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.builder_ai import assemble_template_html, resolve_assembly_inputs
from agents.coremind_agent import ProjectType
from agents.template_ai import load_sector_template_html
from tools.html_markdown import strip_markdown_code_fences


def _plan(category: str, pt: ProjectType) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=pt,
        project_type_label="E-commerce",
        template="dashboard",
        template_label="Dashboard",
        rationale="Test",
        complexity_score=3,
        complexity_label="Moyenne",
        market_price_min=500,
        market_price_max=2000,
        suggested_price_min=200,
        suggested_price_max=800,
        palette=ToolboxPalette(primary="#2563EB", secondary="#F8FAFC", accent="#F59E0B"),
        pricing_category=category,
    )


def test_resolve_assembly_forces_ecommerce_not_dashboard() -> None:
    plan = _plan("ecommerce", ProjectType.SAAS_DASHBOARD)
    wrong = load_sector_template_html("app_dashboard.html")
    html, _name, _sector, _city, tid, _filled = resolve_assembly_inputs(
        user_prompt="boutique pâtisserie Rouen",
        plan=plan,
        research_content=None,
        design_system=None,
        template_html=wrong,
        sector_template={
            "template_id": "app_dashboard",
            "html": wrong,
            "content_filled": True,
        },
    )
    assert tid.startswith("ecommerce_")
    assert "sidebar-brand" not in html.lower() or "panier" in html.lower()


def test_assemble_strips_markdown_fences() -> None:
    plan = _plan("ecommerce", ProjectType.SAAS_DASHBOARD)
    raw = load_sector_template_html("ecommerce_alimentaire.html")
    fenced = f"```html\n{raw}\n```"
    html, _, _, _, tid, _ = resolve_assembly_inputs(
        user_prompt="boutique pâtisserie",
        plan=plan,
        research_content=None,
        design_system=None,
        template_html=fenced,
        sector_template=None,
    )
    assert "```" not in html[:200]
    result = asyncio.run(
        assemble_template_html(
            template_html=html,
            client_name="Maison Dupont",
            sector="commerce",
            city="Rouen",
            user_prompt="boutique pâtisserie",
            template_id=tid,
            skip_content_fill=False,
        )
    )
    assert result.ok
    assert result.data
    assert "```" not in (result.data.html or "")[:300]
    assert strip_markdown_code_fences("```html\n") == ""


def test_resolve_assembly_keeps_generated_template_id() -> None:
    plan = _plan("vitrine_next", ProjectType.SITE_WEB)
    generated_html = (
        "<!DOCTYPE html><html><head><title>{{CLIENT_NAME}}</title></head>"
        "<body><h1>{{CLIENT_NAME}}</h1><p>Commerce Rouen</p></body></html>"
    )
    generated_id = "generated_vitrine_next_commerce"
    html, _name, _sector, _city, tid, _filled = resolve_assembly_inputs(
        user_prompt="vitrine commerce Rouen",
        plan=plan,
        research_content=None,
        design_system=None,
        template_html=generated_html,
        sector_template={
            "template_id": generated_id,
            "html_raw": generated_html,
            "generated": True,
        },
    )
    assert tid == generated_id
    assert "generated_vitrine" in tid
    assert "{{CLIENT_NAME}}" in html
