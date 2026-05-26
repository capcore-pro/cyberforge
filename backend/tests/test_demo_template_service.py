"""Tests démos template — HTML préfabriqué sans React."""

import asyncio
from unittest.mock import AsyncMock, patch

from tools.demo_template_service import (
    TEMPLATE_CRM,
    TEMPLATE_DASHBOARD,
    TEMPLATE_FACTURATION,
    TEMPLATE_LANDING,
    TEMPLATE_MARKERS,
    TEMPLATE_RESERVATION,
    TEMPLATE_TASKFLOW,
    DemoTemplateService,
    build_html_from_seed,
    detect_template_from_prompt,
    heuristic_demo_seed,
    is_valid_demo_html,
    seed_to_code_result,
)


def test_detect_template_invoice() -> None:
    assert detect_template_from_prompt("Application de facturation avec TVA") == TEMPLATE_FACTURATION


def test_detect_template_crm() -> None:
    assert detect_template_from_prompt("CRM pipeline commercial contacts") == TEMPLATE_CRM
    assert detect_template_from_prompt("CRM") == TEMPLATE_CRM


def test_detect_template_dashboard() -> None:
    assert detect_template_from_prompt("Dashboard analytics KPIs", project_type_label="SaaS dashboard") == TEMPLATE_DASHBOARD


def test_detect_template_landing() -> None:
    assert detect_template_from_prompt("Landing page marketing hero témoignages") == TEMPLATE_LANDING


def test_detect_template_reservation() -> None:
    assert detect_template_from_prompt("Application de réservation de tables") == TEMPLATE_RESERVATION


def test_heuristic_seed_reservation_tasks() -> None:
    seed = heuristic_demo_seed(
        "Application de réservation de tables pour restaurant",
        project_type_label="Application web",
    )
    assert any("réservation" in t[0].lower() for t in seed.tasks)
    assert "Acme Corp" not in " ".join(t[0] for t in seed.tasks)


def test_heuristic_seed_restaurant_tasks() -> None:
    seed = heuristic_demo_seed(
        "Site pour mon restaurant italien avec réservations",
        project_type_label="Site web",
    )
    assert seed.template == TEMPLATE_RESERVATION
    assert "restaurant" in seed.brand_name.lower() or "Restaurant" in seed.brand_name
    html = build_html_from_seed(seed).lower()
    assert "couvert" in html or "réservation" in html or "carte" in html or "chef" in html


def test_crm_html_has_no_template_placeholders() -> None:
    seed = heuristic_demo_seed("CRM gestion clients", project_type_label="SaaS")
    html = build_html_from_seed(seed)
    assert TEMPLATE_MARKERS[TEMPLATE_CRM] in html
    assert "{contact.name}" not in html
    assert "saas-shell" not in html
    assert "Jean Dupont" in html
    assert "Marie Martin" in html


def test_default_tasks_are_professional_not_acme() -> None:
    seed = heuristic_demo_seed("Application web interne", project_type_label="SaaS")
    assert seed.template == TEMPLATE_TASKFLOW
    joined = " ".join(t[0] for t in seed.tasks)
    assert "Acme Corp" not in joined
    assert "comité de direction" in joined.lower() or "reporting" in joined.lower()


def test_build_html_all_templates_valid() -> None:
    prompts = {
        TEMPLATE_TASKFLOW: ("App SaaS gestion de tâches", "SaaS"),
        TEMPLATE_LANDING: ("Landing page vitrine marketing", "Site web"),
        TEMPLATE_CRM: ("CRM contacts pipeline commercial", "SaaS"),
        TEMPLATE_DASHBOARD: ("Dashboard analytics KPIs", "SaaS dashboard"),
        TEMPLATE_FACTURATION: ("Facturation devis TVA", "Application web"),
        TEMPLATE_RESERVATION: ("Réservation créneaux restaurant", "Application web"),
    }
    for template, (prompt, label) in prompts.items():
        seed = heuristic_demo_seed(prompt, project_type_label=label)
        assert seed.template == template
        html = build_html_from_seed(seed)
        assert TEMPLATE_MARKERS[template] in html
        assert is_valid_demo_html(html, template)
        assert "export default" not in html
        assert "import React" not in html


def test_build_client_demo_generation_no_html_llm() -> None:
    with patch.object(
        DemoTemplateService,
        "resolve_seed",
        new_callable=AsyncMock,
    ) as mock_seed:
        from tools.demo_template_service import DemoSeedData

        mock_seed.return_value = DemoSeedData(
            template="taskflow",
            title="Boulangerie Dupont",
            subtitle="Gérez vos commandes",
            brand_name="Boulangerie Dupont",
            brand_tag="Artisan",
            user_name="Marie Dupont",
            user_role="Gérante",
            tasks=(("Préparer les commandes du matin", False),),
        )
        result = asyncio.run(
            DemoTemplateService().build_client_demo_generation(
                user_prompt="boulangerie",
                project_type_label="Site web",
            )
        )
    assert result.model == "cyberforge-premium"
    assert result.provider == "cyberforge"
    assert "saas-shell" in result.code
    assert not any(f.path.endswith(".tsx") for f in result.files)


def test_marketing_agency_dashboard_context() -> None:
    seed = heuristic_demo_seed(
        "Dashboard pour une agence marketing : campagnes, leads, ROI et clics",
        project_type_label="SaaS / tableau de bord",
    )
    assert seed.template == TEMPLATE_DASHBOARD
    html = build_html_from_seed(seed)
    blob = html.lower()
    assert "lead" in blob or "campagne" in blob or "roi" in blob or "clic" in blob


def test_real_estate_crm_context() -> None:
    seed = heuristic_demo_seed(
        "CRM immobilier pour mandats, visites et acheteurs",
        project_type_label="Application web",
    )
    assert seed.template == TEMPLATE_CRM
    html = build_html_from_seed(seed)
    blob = html.lower()
    assert "mandat" in blob or "visite" in blob or "appartement" in blob or "immobilier" in blob


def test_seed_to_code_result_index_html_only() -> None:
    seed = heuristic_demo_seed("Dashboard analytics", project_type_label="SaaS")
    assert seed.template == TEMPLATE_DASHBOARD
    gen = seed_to_code_result(seed, summary="test")
    assert gen.files[0].path == "index.html"
    assert gen.files[0].content.startswith("<!DOCTYPE")
    assert TEMPLATE_MARKERS[TEMPLATE_DASHBOARD] in gen.code
