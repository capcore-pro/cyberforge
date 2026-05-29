"""Tests ArchitectAI."""

import asyncio

import pytest

from agents.architect_agent import ArchitectAgent, parse_type_prefix, resolve_forced_type_token
from agents.coremind_agent import ProjectType
from tools.demo_template_service import TEMPLATE_CRM, TEMPLATE_LANDING


def test_parse_type_prefix_multiline() -> None:
    token, body = parse_type_prefix("TYPE: vitrine_next\nSite pour boulangerie")
    assert token == "vitrine_next"
    assert "boulangerie" in body


def test_parse_type_prefix_inline() -> None:
    token, body = parse_type_prefix("TYPE: ecommerce Boutique en ligne")
    assert token == "ecommerce"
    assert "Boutique" in body


def test_resolve_forced_type_vitrine_next() -> None:
    pt, cat, mode = resolve_forced_type_token("vitrine_next")
    assert pt == ProjectType.SITE_WEB
    assert cat == "vitrine_next"
    assert mode == "vitrine_next"


def test_architect_type_prefix_forces_category() -> None:
    agent = ArchitectAgent()
    plan, analysis = asyncio.run(
        agent.plan_with_analysis("TYPE: vitrine_next\nLanding simple pour café")
    )
    assert plan.pricing_category == "vitrine_next"
    assert analysis.project_type == ProjectType.SITE_WEB
    assert "TYPE:" in plan.rationale or "imposé" in plan.rationale.lower()


def test_architect_type_prefix_beats_reservation_in_service_list() -> None:
    agent = ArchitectAgent()
    plan, _ = asyncio.run(
        agent.plan_with_analysis(
            "TYPE: vitrine_next\nNous proposons audit, conseil et réservation d'ateliers."
        )
    )
    assert plan.pricing_category == "vitrine_next"


def test_architect_detects_crm_template() -> None:
    agent = ArchitectAgent()
    plan, analysis = asyncio.run(
        agent.plan_with_analysis(
            "Je veux un CRM pour gérer mes contacts clients et le pipeline commercial"
        )
    )
    assert plan.template == TEMPLATE_CRM
    assert plan.project_type in (ProjectType.SAAS_DASHBOARD, ProjectType.APPLICATION_WEB)
    assert analysis.complexity_score >= 1
    assert 1 <= plan.complexity_score <= 10
    assert plan.complexity_label in ("Simple", "Moyenne", "Complexe")
    assert plan.market_price_max >= plan.market_price_min > 0
    assert plan.suggested_price_max >= plan.suggested_price_min > 0


def test_architect_landing_hint() -> None:
    agent = ArchitectAgent()
    plan, _ = asyncio.run(
        agent.plan_with_analysis(
            "Landing page marketing avec hero et CTA pour startup",
            project_type_hint=ProjectType.LANDING_PAGE,
        )
    )
    assert plan.template in (TEMPLATE_LANDING, "taskflow", "landing")
    assert "Landing" in plan.project_type_label or plan.project_type == ProjectType.LANDING_PAGE
