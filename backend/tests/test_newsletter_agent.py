"""Tests newsletter_agent — DeepSeek mocké."""

from __future__ import annotations

import asyncio
import importlib
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture()
def newsletter_stack(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "newsletter_agent.db"
        import cockpit_db
        import newsletter_db
        import newsletter_agent

        importlib.reload(cockpit_db)
        importlib.reload(newsletter_db)
        importlib.reload(newsletter_agent)
        monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
        cockpit_db.init_db()
        yield newsletter_agent, newsletter_db


def test_analyze_contact_saves_personality(newsletter_stack) -> None:
    asyncio.run(_test_analyze_contact_saves_personality(newsletter_stack))


async def _test_analyze_contact_saves_personality(newsletter_stack) -> None:
    agent, db = newsletter_stack
    ctx = {
        "source": "managed",
        "project_id": "proj-abc",
        "client_name": "Boulangerie Le Fournil",
        "company": "Boulangerie Le Fournil",
        "project_type": "vitrine_next",
        "sector": "boulangerie",
        "site_url": "https://fournil.vercel.app",
        "prompt": "Site vitrine boulangerie artisanale",
        "client_email": "contact@fournil.fr",
    }
    llm_json = {
        "personality_tone": "chaleureux",
        "key_values": ["artisanat", "proximité", "fraîcheur"],
        "communication_style": "Ton convivial et concret.",
        "ice_breaker": "Votre fournil mérite une vitrine aussi bonne que vos croissants.",
    }

    with (
        patch.object(
            agent,
            "_fetch_project_context",
            new=AsyncMock(return_value=ctx),
        ),
        patch.object(
            agent,
            "_call_deepseek_json",
            new=AsyncMock(return_value=llm_json),
        ),
    ):
        result = await agent.analyze_contact("proj-abc")

    assert result["personality_tone"] == "chaleureux"
    contact = db.get_contact_by_email("contact@fournil.fr")
    assert contact is not None
    notes = json.loads(contact["personality_notes"])
    assert notes["ice_breaker"]


def test_generate_welcome_sequence(newsletter_stack) -> None:
    asyncio.run(_test_generate_welcome_sequence(newsletter_stack))


async def _test_generate_welcome_sequence(newsletter_stack) -> None:
    agent, db = newsletter_stack
    contact = db.add_contact(
        email="test@example.com",
        name="Jean",
        company="Test Co",
        sector="ecommerce",
        project_type="ecommerce",
        personality_notes=json.dumps(
            {
                "personality_tone": "professionnel",
                "key_values": ["a", "b", "c"],
                "communication_style": "Direct",
                "ice_breaker": "Hello",
            }
        ),
    )
    welcome_payload = {
        "emails": [
            {
                "type": "welcome_j0",
                "subject": "Votre site est en ligne",
                "html_body": "<p>Bienvenue Jean</p>",
            },
            {
                "type": "welcome_j1",
                "subject": "Comment bien démarrer",
                "html_body": "<p>3 actions</p>",
            },
            {
                "type": "welcome_j3",
                "subject": "Un retour ?",
                "html_body": "<p>Feedback</p>",
            },
        ]
    }

    with patch.object(
        agent,
        "_call_deepseek_json",
        new=AsyncMock(return_value=welcome_payload),
    ):
        emails = await agent.generate_welcome_sequence(contact["id"])

    assert len(emails) == 3
    assert {e["type"] for e in emails} == {
        "welcome_j0",
        "welcome_j1",
        "welcome_j3",
    }
