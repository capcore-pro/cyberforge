"""Tests ContentAI — contenu client réel, sans placeholders interdits."""

from __future__ import annotations

import asyncio
import re

import pytest

from agents.content_ai import (
    build_content_slots,
    fill_template_content,
)
from agents.design_system_ai import build_design_system
from agents.template_ai import load_sector_template_html
from core.agent_contract import require_ok


def _raw_alimentaire() -> str:
    return load_sector_template_html("vitrine_alimentaire.html")


def test_hero_title_mentions_city_and_sector() -> None:
    slots = build_content_slots(
        client_name="Aux Délices",
        sector="restauration",
        city="Rouen",
        template_html=_raw_alimentaire(),
        research_content={
            "mots_cles": ["pain au levain", "viennoiserie", "pâtisserie"],
            "ville": "Rouen",
            "secteur": "boulangerie",
        },
        template_id="vitrine_alimentaire",
        user_prompt="Boulangerie Aux Délices à Rouen",
    )
    title = slots["HERO_TITLE"].lower()
    assert "rouen" in title or "délices" in title
    assert "service 1" not in title


def test_services_not_generic() -> None:
    slots = build_content_slots(
        client_name="Plomberie Martin",
        sector="artisanat",
        city="Lille",
        template_html=load_sector_template_html("vitrine_artisan.html"),
        research_content={"mots_cles": ["dépannage", "chauffe-eau"]},
        template_id="vitrine_artisan",
    )
    for key in ("SERVICE_1", "SERVICE_2", "SERVICE_3"):
        assert "service 1" not in slots[key].lower()
        assert "service 2" not in slots[key].lower()
        assert len(slots[key]) > 4


def test_fill_complete_html() -> None:
    ds = require_ok(
        build_design_system(
            sector="restauration",
            client_name="Aux Délices",
            project_type="site_web",
            user_prompt="Boulangerie Rouen",
        )
    )
    result = fill_template_content(
        template_html=_raw_alimentaire(),
        client_name="Aux Délices",
        sector="restauration",
        city="Rouen",
        research_content={
            "nom_entreprise": "Aux Délices",
            "ville": "Rouen",
            "mots_cles": ["pain", "viennoiserie", "sandwichs"],
        },
        design_system=ds.to_contract_dict(),
        template_id="vitrine_alimentaire",
        user_prompt="Boulangerie artisanale Rouen",
    )
    data = require_ok(result)
    assert "{{" not in data.html
    assert "lorem" not in data.html.lower()
    assert "Service 1" not in data.html
    assert "Aux Délices" in data.html
    assert ds.colors.primary in data.html
    assert "cf-design-system" in data.html


def test_forbidden_lorem_fails() -> None:
    bad_template = _raw_alimentaire().replace(
        "{{HERO_SUBTITLE}}",
        "Lorem ipsum dolor sit amet",
    )
    result = fill_template_content(
        template_html=bad_template,
        client_name="Test Client",
        sector="commerce",
        city="Paris",
        template_id="vitrine_default",
    )
    assert not result.ok


def test_agent_async() -> None:
    from agents.content_ai import ContentAgent

    agent = ContentAgent()

    async def _run():
        return await agent.fill(
            template_html=_raw_alimentaire(),
            client_name="Le Fournil",
            sector="restauration",
            city="Nantes",
            template_id="vitrine_alimentaire",
        )

    result = asyncio.run(_run())
    assert result.ok
    assert "{{" not in result.data.html  # type: ignore[union-attr]
