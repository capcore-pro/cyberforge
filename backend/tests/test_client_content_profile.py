"""Tests profil contenu client — injection littérale HTML."""

from __future__ import annotations

from agents.research_agent import ResearchBrief
from tools.client_content_profile import (
    build_client_content_profile,
    repair_client_literals_in_html,
    validate_client_literals,
)


def test_enforce_client_literals_injects_title_and_h1() -> None:
    html = "<!DOCTYPE html><html><head></head><body><p>Services</p></body></html>"
    profile = build_client_content_profile(
        research_brief=ResearchBrief(
            nom_entreprise="Boulangerie Martin",
            secteur="boulangerie",
            ville="Lyon",
            mots_cles=["pain", "viennoiserie", "artisan"],
        ),
    )
    out = repair_client_literals_in_html(html, profile)
    assert "Boulangerie Martin" in out
    assert "<title>" in out.lower()
    assert "Lyon" in out
    assert "Boulangerie" in out
    assert "pain" in out.lower()
    assert "viennoiserie" in out.lower()


def test_validate_client_literals_requires_name_twice() -> None:
    profile = build_client_content_profile(
        research_brief=ResearchBrief(
            nom_entreprise="Dupont SARL",
            secteur="plomberie",
            ville="Nantes",
        ),
    )
    issues = validate_client_literals(
        "<html><h1>Dupont SARL</h1><p>plomberie Nantes</p></html>",
        profile,
    )
    assert any(code == "missing_client_name" for code, _ in issues)

    ok_html = (
        "<html><head><title>Dupont SARL</title></head>"
        "<body><h1>Dupont SARL</h1>"
        "<p>plomberie à Nantes — Dupont SARL</p></body></html>"
    )
    assert not validate_client_literals(ok_html, profile)


def test_build_profile_from_research_brief_dict() -> None:
    profile = build_client_content_profile(
        research_brief={
            "nom_entreprise": "Studio Lumière",
            "secteur": "photographie",
            "ville": "Bordeaux",
            "mots_cles": ["portrait", "mariage", "studio"],
        },
    )
    assert profile.company_name == "Studio Lumière"
    assert profile.sector == "photographie"
    assert len(profile.keywords) == 3
