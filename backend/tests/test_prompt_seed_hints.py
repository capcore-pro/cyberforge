"""Tests extraction signaux métier pour seeds premium."""

from tools.demo_template_service import build_html_from_seed, enrich_demo_seed, heuristic_demo_seed
from tools.prompt_seed_hints import extract_campaign_names
from tools.premium_seed_context import detect_demo_vertical


def test_detect_marketing_from_agency_prompt() -> None:
    blob = "Dashboard pour une agence marketing : campagnes été, leads, ROI, clics"
    assert detect_demo_vertical(blob, project_type_label="SaaS / tableau de bord") == "marketing"


def test_extract_campaign_names_from_prompt() -> None:
    names = extract_campaign_names(
        'Campagne "Été Luxe Retail" et campagne Black Friday SEA'
    )
    assert any("été" in n.lower() or "luxe" in n.lower() for n in names)


def test_marketing_dashboard_html_has_campaign_metrics() -> None:
    seed = enrich_demo_seed(
        heuristic_demo_seed(
            "Dashboard agence marketing — campagne Performance SEA, leads, ROI, clics",
            project_type_label="SaaS / tableau de bord",
        )
    )
    html = build_html_from_seed(seed).lower()
    assert "lead" in html or "campagne" in html or "roi" in html or "clic" in html


def test_restaurant_html_culinary_content() -> None:
    seed = enrich_demo_seed(
        heuristic_demo_seed(
            "Application pour mon restaurant italien — réservations et carte des plats",
            project_type_label="Application web",
        )
    )
    html = build_html_from_seed(seed).lower()
    assert seed.template == "reservation" or "restaurant" in html or "couvert" in html or "carte" in html
