"""BuilderAI — assemblage forcé sans fallback CoreMind."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.builder_agent import must_force_sector_template_assembly
from agents.coremind_agent import ProjectType


def _plan(category: str, pt: ProjectType = ProjectType.SAAS_DASHBOARD) -> ArchitectPlan:
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


def test_force_assembly_ecommerce_with_sector_html() -> None:
    plan = _plan("ecommerce")
    html = "<!DOCTYPE html><html><body>" + "x" * 300 + "</body></html>"
    assert must_force_sector_template_assembly(
        plan, sector_template_html=html, sector_template=None
    )


def test_no_force_without_sector_html() -> None:
    plan = _plan("ecommerce")
    assert not must_force_sector_template_assembly(
        plan, sector_template_html=None, sector_template=None
    )
