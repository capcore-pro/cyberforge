"""Tests VitrineContentAI — validation et repli exemple."""

import asyncio

import pytest

from tools.vitrine.content_agent import VitrineContentAgent, VitrineContentError
from tools.vitrine.content_schema import ClientBranding
from tools.vitrine.scaffold_renderer import load_example_content


def test_generate_short_prompt_raises() -> None:
    agent = VitrineContentAgent()
    with pytest.raises(VitrineContentError):
        asyncio.run(agent.generate("ab"))


def test_generate_fallback_without_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = VitrineContentAgent()

    async def _no_llm(_user_msg: str):
        return None

    monkeypatch.setattr(agent, "_generate_full_json", _no_llm)
    content = asyncio.run(
        agent.generate(
            "Site vitrine pour Boulangerie Martin à Lyon, pain artisanal",
            project_type_label="Site vitrine",
        )
    )
    assert content.meta.businessName
    assert content.home.hero.title


def test_apply_branding_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = VitrineContentAgent()
    branding = ClientBranding(
        company="Électricité Pro",
        phone="01 23 45 67 89",
        email="contact@elec-pro.fr",
        primary_color="#ff5500",
    )

    async def _no_llm(_user_msg: str):
        return None

    monkeypatch.setattr(agent, "_generate_full_json", _no_llm)
    content = asyncio.run(
        agent.generate(
            "Électricien urgence 24h",
            branding=branding,
        )
    )

    assert content.meta.businessName == "Électricité Pro"
    assert content.meta.primaryColor == "#ff5500"
    assert content.footer.phone == "01 23 45 67 89"


def test_example_content_validates() -> None:
    content = load_example_content()
    assert content.contactPage.fields.submit
