"""Tests catalogue templates sectoriels multi-types."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.coremind_agent import ProjectType
from tools.sector_template_catalog import (
    resolve_sector_template_from_plan,
    resolve_vitrine_template_file,
    template_file_path,
)


def _plan(category: str, pt: ProjectType = ProjectType.SITE_WEB) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=pt,
        project_type_label="Test",
        template="landing",
        template_label="Landing",
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


def test_ecommerce_boulangerie_template() -> None:
    plan = _plan("ecommerce", ProjectType.APPLICATION_WEB)
    tid, fname = resolve_sector_template_from_plan(
        plan, "boulangerie", "boutique boulangerie Rouen"
    )
    assert tid == "ecommerce_alimentaire"
    assert template_file_path(fname).is_file()


def test_reservation_coiffure_template() -> None:
    plan = _plan("site_reservation")
    tid, _ = resolve_sector_template_from_plan(plan, "coiffure", "salon coiffure Lyon")
    assert tid == "reservation_beaute"


def test_app_crm_template() -> None:
    plan = _plan("application_web", ProjectType.APPLICATION_WEB)
    tid, _ = resolve_sector_template_from_plan(plan, "commerce", "crm pipeline clients")
    assert tid == "app_crm"


def test_desktop_gestion_template() -> None:
    plan = _plan("application_desktop", ProjectType.APPLICATION_DESKTOP)
    tid, _ = resolve_sector_template_from_plan(plan, "gestion", "logiciel gestion stock")
    assert tid == "desktop_gestion"


def test_vitrine_fallback() -> None:
    fname = resolve_vitrine_template_file("boulangerie", "boulangerie artisanale")
    assert fname == "vitrine_alimentaire.html"
