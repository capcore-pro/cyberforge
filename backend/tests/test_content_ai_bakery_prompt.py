"""ContentAI — nom fictif crédible sans client explicite dans le prompt."""

from agents.content_ai import build_content_slots
from agents.template_ai import load_sector_template_html


def test_boulangerie_rouen_prompt_uses_fictional_brand() -> None:
    slots = build_content_slots(
        client_name="",
        sector="boulangerie",
        city="Rouen",
        template_html=load_sector_template_html("vitrine_alimentaire.html"),
        research_content={
            "nom_entreprise": "artisanale",
            "ville": "Rouen",
            "secteur": "boulangerie",
            "mots_cles": ["pain", "viennoiserie"],
        },
        template_id="vitrine_alimentaire",
        user_prompt="vitrine boulangerie artisanale Rouen",
    )
    brand = slots["CLIENT_NAME"].lower()
    assert "artisanale" not in brand
    assert "rouen" in brand or "fournil" in brand or "boulangerie" in brand
    assert "service 1" not in slots["HERO_TITLE"].lower()
