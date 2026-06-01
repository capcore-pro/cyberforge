"""ContentAI — placeholders contact par défaut (jamais de 422)."""

from __future__ import annotations

from agents.content_ai import build_content_slots, fill_template_content
from agents.template_ai import load_sector_template_html
from core.agent_contract import require_ok


def test_ecommerce_slots_include_contact_without_client_details() -> None:
    slots = build_content_slots(
        client_name="",
        sector="boulangerie",
        city="",
        template_html=load_sector_template_html("ecommerce_alimentaire.html"),
        research_content={"mots_cles": ["pain", "viennoiserie"]},
        template_id="ecommerce_alimentaire",
        user_prompt="boutique pâtisserie artisanale",
    )
    assert slots["ADDRESS"]
    assert slots["EMAIL"]
    assert slots["PHONE"]
    assert "@" in slots["EMAIL"]
    assert slots["ADDRESS"] == "France" or "France" in slots["ADDRESS"]


def test_ecommerce_rouen_normandy_defaults() -> None:
    slots = build_content_slots(
        client_name="Aux Délices",
        sector="boulangerie",
        city="Rouen",
        template_html=load_sector_template_html("ecommerce_alimentaire.html"),
        template_id="ecommerce_alimentaire",
        user_prompt="boutique pâtisserie Rouen",
    )
    assert "Rouen" in slots["ADDRESS"]
    assert "Normandie" in slots["ADDRESS"]
    assert "02 35" in slots["PHONE"]
    assert "contact@" in slots["EMAIL"]
    assert ".fr" in slots["EMAIL"]


def test_fill_ecommerce_no_unfilled_placeholders() -> None:
    result = fill_template_content(
        template_html=load_sector_template_html("ecommerce_alimentaire.html"),
        client_name="",
        sector="boulangerie",
        city="Rouen",
        template_id="ecommerce_alimentaire",
        user_prompt="ecommerce pâtisserie Rouen",
    )
    data = require_ok(result)
    assert "{{" not in data.html
    assert "02 35" in data.html or "À préciser" in data.html
