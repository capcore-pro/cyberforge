"""Tests profil contenu client — injection littérale HTML."""

from __future__ import annotations

import re

import pytest

from agents.research_agent import ResearchBrief
from tools.client_content_profile import (
    build_client_content_profile,
    generate_fictional_business_name,
    humanize_sector_label,
    is_blocked_demo_identity,
    is_plausible_business_name,
    looks_like_technical_placeholder,
    repair_client_literals_in_html,
    resolve_client_business_name,
    safe_contact_email_domain_slug,
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
    assert 'name="keywords"' in out.lower()
    assert "pain" in out.lower()  # meta keywords, pas corps visible forcé
    assert "viennoiserie" in out.lower()
    body_no_meta = re.sub(r"<head[\s\S]*?</head>", "", out, flags=re.I)
    assert "<li>pain</li>" not in body_no_meta.lower()


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


def test_artisanale_is_not_a_business_name() -> None:
    assert not is_plausible_business_name("artisanale")
    name = resolve_client_business_name(
        "artisanale",
        sector="boulangerie",
        city="Rouen",
        user_prompt="vitrine boulangerie artisanale Rouen",
    )
    assert name != "artisanale"
    assert "Rouen" in name or "Fournil" in name or "Boulangerie" in name


def test_fictional_bakery_name_for_rouen() -> None:
    name = generate_fictional_business_name(
        sector="boulangerie",
        city="Rouen",
        user_prompt="vitrine boulangerie artisanale Rouen",
    )
    assert "artisanale" not in name.lower()
    assert len(name) >= 8


def test_blocked_demo_identities_never_used_as_brand() -> None:
    for blocked in (
        "Loi Visuelle",
        "contact@loivisuelle.fr",
        "Sophie",
        "Camille",
        "Léa",
        "Institut de beauté",
    ):
        assert is_blocked_demo_identity(blocked)
        assert not is_plausible_business_name(blocked)

    profile = build_client_content_profile(
        user_prompt="Loi Visuelle — institut de beauté avec Sophie et Camille",
        research_brief={
            "nom_entreprise": "Loi Visuelle",
            "secteur": "beauté",
            "ville": "Lyon",
        },
    )
    assert "loi" not in profile.company_name.lower()
    assert "visuelle" not in profile.company_name.lower()
    assert profile.company_name != "Sophie"
    assert safe_contact_email_domain_slug("Loi Visuelle") == "entreprise"
    assert "loivisuelle" not in safe_contact_email_domain_slug("Loi Visuelle")


def test_beauty_sector_label_is_generic() -> None:
    label = humanize_sector_label("beauté", user_prompt="spa esthétique")
    assert label == "Beauté & bien-être"
    assert label != "Institut de beauté"


def test_french_common_names_are_plausible_brands() -> None:
    for name in (
        "Laurier",
        "Beau",
        "Camping Les Étoiles",
        "L'Étoile Rose",
        "Rose",
        "Vert",
        "Boulangerie",
        "Commerce Local",
    ):
        assert is_plausible_business_name(name), name


@pytest.mark.skip(reason="DÉSACTIVÉ TEMPORAIREMENT - DEBUG — FORBIDDEN_CONTENT_PATTERNS")
def test_technical_placeholders_rejected() -> None:
    for bad in (
        "lorem ipsum",
        "NOM_CLIENT",
        "votre_nom",
        "test123",
        "Example Corp",
        "undefined",
    ):
        assert looks_like_technical_placeholder(bad)
        assert not is_plausible_business_name(bad)


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
