"""Tests analyse complexité et tarification ArchitectAI."""

import asyncio

from agents.architect_agent import ArchitectAgent
from agents.architect_pricing import (
    analyze_prompt_complexity,
    build_complexity_pricing,
    complexity_label_from_score,
    resolve_pricing_category,
    _prompt_triggers_site_reservation,
)
from agents.coremind_agent import ProjectType


def test_complexity_labels() -> None:
    assert complexity_label_from_score(2) == "Simple"
    assert complexity_label_from_score(5) == "Moyenne"
    assert complexity_label_from_score(9) == "Complexe"


def test_ecommerce_prompt_high_complexity() -> None:
    prompt = (
        "Boutique e-commerce avec panier, paiement Stripe, catalogue produits, "
        "auth OAuth, admin dashboard et 8 pages."
    )
    score = analyze_prompt_complexity(prompt)
    assert score >= 7
    category = resolve_pricing_category(ProjectType.APPLICATION_WEB, prompt)
    assert category == "ecommerce"
    pricing = build_complexity_pricing(prompt, ProjectType.APPLICATION_WEB)
    assert pricing["market_price_min"] == 6000
    assert pricing["market_price_max"] == 15000
    assert pricing["suggested_price_min"] == int(6000 * 0.4)
    assert pricing["suggested_price_max"] == int(15000 * 0.4)


def test_site_reservation_not_triggered_by_service_list() -> None:
    prompt = (
        "Site vitrine pour notre agence. Nous proposons conseil, audit, "
        "formation et réservation d'ateliers sur devis."
    )
    assert _prompt_triggers_site_reservation(prompt) is False
    assert (
        resolve_pricing_category(ProjectType.SITE_WEB, prompt) == "vitrine_next"
    )


def test_site_reservation_triggered_when_primary_subject() -> None:
    prompt = "Application de réservation de tables pour restaurant italien"
    assert _prompt_triggers_site_reservation(prompt) is True
    assert resolve_pricing_category(ProjectType.SITE_WEB, prompt) == "site_reservation"


def test_vitrine_generation_mode() -> None:
    pricing = build_complexity_pricing(
        "Site vitrine PME avec accueil et contact",
        ProjectType.SITE_WEB,
        generation_mode="vitrine_next",
    )
    assert pricing["pricing_category"] == "vitrine_next"
    assert pricing["market_price_min"] >= 300


def test_architect_plan_includes_pricing() -> None:
    agent = ArchitectAgent()
    plan, _ = asyncio.run(
        agent.plan_with_analysis(
            "Extension Chrome pour sauvegarder des onglets",
            project_type_hint=ProjectType.EXTENSION_NAVIGATEUR,
        )
    )
    assert 1 <= plan.complexity_score <= 10
    assert plan.complexity_label in ("Simple", "Moyenne", "Complexe")
    assert plan.market_price_max >= plan.market_price_min
    assert plan.suggested_price_max >= plan.suggested_price_min
    assert plan.pricing_category == "extension_navigateur"
