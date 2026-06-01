"""Tests assemblage template-first ecommerce / réservation."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.builder_ai import assemble_template_html, uses_template_assembly
from agents.content_ai import build_content_slots
from agents.coremind_agent import ProjectType
from agents.template_ai import load_sector_template_raw
from core.agent_contract import require_ok


def _plan(category: str, pt: ProjectType = ProjectType.APPLICATION_WEB) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=pt,
        project_type_label="Projet test",
        template="landing",
        template_label="Landing",
        rationale="Test",
        complexity_score=3,
        complexity_label="Moyenne",
        market_price_min=800,
        market_price_max=3000,
        suggested_price_min=300,
        suggested_price_max=1200,
        palette=ToolboxPalette(primary="#2563EB", secondary="#F8FAFC", accent="#10B981"),
        pricing_category=category,
    )


def test_uses_template_assembly_ecommerce() -> None:
    assert uses_template_assembly(_plan("ecommerce"), generation_mode="client_demo")


def test_ecommerce_content_slots_no_generic() -> None:
    from agents.template_ai import load_sector_template_html

    raw = load_sector_template_html("ecommerce_default.html")
    slots = build_content_slots(
        client_name="",
        sector="ecommerce",
        city="Paris",
        template_html=raw,
        template_id="ecommerce_default",
        user_prompt="boutique en ligne mode Paris",
    )
    assert "Service 1" not in slots["PRODUCT_1_NAME"]
    assert slots["CLIENT_NAME"]
    assert slots["PRODUCT_1_PRICE"]


def test_ecommerce_assembly_fills_placeholders() -> None:
    plan = _plan("ecommerce")
    loaded = require_ok(
        load_sector_template_raw(sector="alimentaire", user_prompt="boutique bio", plan=plan)
    )
    result = require_ok(
        assemble_template_html(
            template_html=loaded.html,
            client_name="",
            sector="alimentaire",
            city="Lyon",
            user_prompt="ecommerce épicerie Lyon",
            template_id=loaded.template_id,
        )
    )
    assert "{{" not in result.html
    assert "add-cart" in result.html.lower()
    assert len(result.html) > 800
