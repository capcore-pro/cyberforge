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


def test_salon_coiffure_prompt_resolves_site_reservation_not_ecommerce() -> None:
    from agents.architect_pricing import resolve_pricing_category
    from agents.coremind_agent import ProjectType

    category = resolve_pricing_category(
        ProjectType.SITE_WEB,
        "salon de coiffure à Rouen avec prise de rendez-vous",
    )
    assert category == "site_reservation"
    plan = _plan("site_reservation", ProjectType.SITE_WEB)
    tid, fname = resolve_sector_template_from_plan(
        plan, "coiffure", "salon de coiffure Rouen"
    )
    assert tid == "reservation_beaute"
    assert fname.startswith("reservation_")
    assert not tid.startswith("ecommerce_")


def test_site_reservation_category_never_maps_ecommerce_family() -> None:
    from tools.sector_template_catalog import resolve_template_family_from_plan

    plan = _plan("site_reservation", ProjectType.SAAS_DASHBOARD)
    assert resolve_template_family_from_plan(plan) == "reservation"


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


def test_ecommerce_patisserie_rouen_not_app_dashboard() -> None:
    """E-commerce + prompt pâtisserie → ecommerce_alimentaire, jamais app_*."""
    plan = _plan("ecommerce", ProjectType.SAAS_DASHBOARD)
    tid, fname = resolve_sector_template_from_plan(
        plan, "commerce", "boutique pâtisserie Rouen"
    )
    assert tid == "ecommerce_alimentaire"
    assert fname.startswith("ecommerce_")
    assert not tid.startswith("app_")


def test_saas_dashboard_pt_maps_ecommerce_even_with_application_web_category() -> None:
    """Carte E-commerce UI : saas_dashboard ne doit pas retomber sur app_dashboard."""
    plan = _plan("application_web", ProjectType.SAAS_DASHBOARD)
    tid, _ = resolve_sector_template_from_plan(
        plan, "commerce", "catalogue produits en ligne"
    )
    assert tid.startswith("ecommerce_")
    assert tid != "app_dashboard"


def test_ecommerce_category_overrides_application_web_pt() -> None:
    plan = _plan("ecommerce", ProjectType.APPLICATION_WEB)
    tid, _ = resolve_sector_template_from_plan(
        plan, "commerce", "tableau de bord ventes"
    )
    assert tid.startswith("ecommerce_")
    assert tid != "app_dashboard"


def test_application_web_stays_app_family_despite_boutique_in_prompt() -> None:
    plan = _plan("application_web", ProjectType.APPLICATION_WEB)
    tid, _ = resolve_sector_template_from_plan(
        plan, "commerce", "boutique pâtisserie Rouen"
    )
    assert tid.startswith("app_")
    assert not tid.startswith("ecommerce_")
