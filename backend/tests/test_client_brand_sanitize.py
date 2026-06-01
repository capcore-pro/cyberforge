"""Tests nom client court — pas de prompt dans title/h1."""

from __future__ import annotations

from agents.research_agent import ResearchBrief
from tools.client_content_profile import (
    build_client_content_profile,
    format_client_page_title,
    sanitize_brand_name,
)


def test_sanitize_rejects_prompt_fragment() -> None:
    long_prompt = (
        "Cette vitrine de boulangerie et de pâtisserie. Si tu es à Rouen, crée un site…"
    )
    assert sanitize_brand_name(long_prompt, user_prompt=long_prompt) != long_prompt[:50]


def test_format_title_boulangerie() -> None:
    profile = build_client_content_profile(
        user_prompt="Site vitrine pour Aux Délices, boulangerie à Rouen",
        research_brief=ResearchBrief(
            nom_entreprise="Aux Délices",
            secteur="commerce",
            ville="Rouen",
            mots_cles=["pain", "viennoiserie", "boulangerie"],
        ),
    )
    title = format_client_page_title(
        profile,
        user_prompt="Site vitrine pour Aux Délices, boulangerie à Rouen",
        html='<span class="logo">🍞 Aux Délices</span>',
    )
    assert "Aux Délices" in title
    assert "Boulangerie" in title
    assert "Rouen" in title
    assert "Si tu es" not in title
    assert len(title) < 60
