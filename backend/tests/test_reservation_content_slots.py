"""ContentAI — site réservation : prestations et navbar, pas produits e-commerce."""

from __future__ import annotations

import asyncio

from agents.content_ai import build_content_slots, fill_template_content
from agents.template_ai import load_sector_template_html
from core.agent_contract import require_ok


def test_reservation_beaute_services_not_product_packs() -> None:
    slots = build_content_slots(
        client_name="Salon Élégance",
        sector="coiffure",
        city="Rouen",
        template_html=load_sector_template_html("reservation_beaute.html"),
        research_content={"mots_cles": ["saas", "solutions", "pack essentiel"]},
        template_id="reservation_beaute",
        user_prompt="salon de coiffure Rouen",
    )
    assert slots["SERVICE_1"] == "Coupe femme"
    assert slots["SERVICE_1_PRICE"] == "45"
    assert "pack" not in slots["SERVICE_1"].lower()
    assert slots["NAV_SERVICES"] == "Services"
    assert slots["NAV_TARIFS"] == "Tarifs"
    assert slots["SERVICE_CAT_1"] == "Coupes"
    assert "PRODUCT_1_NAME" not in slots
    assert slots["CLIENT_TAGLINE"]
    assert slots["CLIENT_DESCRIPTION"] == slots["CLIENT_TAGLINE"]
    assert slots["SECTOR_LABEL"] == "Coiffure"
    assert slots["TEAM_MEMBER_1"] == "Conseillère beauté"
    assert slots["CLIENT_EMAIL"].startswith("contact@")
    assert "Sophie" not in slots["TEAM_MEMBER_1"]


def test_fill_reservation_beaute_no_ecommerce_markers() -> None:
    result = asyncio.run(
        fill_template_content(
            template_html=load_sector_template_html("reservation_beaute.html"),
            client_name="Salon Élégance",
            sector="coiffure",
            city="Rouen",
            template_id="reservation_beaute",
            user_prompt="salon de coiffure",
        )
    )
    data = require_ok(result)
    assert "{{" not in data.html
    assert "add-cart" not in data.html.lower()
    assert "Coupe femme" in data.html
    assert "Tarifs" in data.html
    assert "Réservation" in data.html
    assert "Sophie" not in data.html
    assert "Coiffure — soins" in data.html
