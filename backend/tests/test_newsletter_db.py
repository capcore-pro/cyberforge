"""Tests newsletter_db — contacts, séquences, emails."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def newsletter_db_module(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "newsletter_test.db"
        import cockpit_db
        import newsletter_db

        importlib.reload(cockpit_db)
        importlib.reload(newsletter_db)
        monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
        cockpit_db.init_db()
        yield newsletter_db


def test_contact_and_sequence_flow(newsletter_db_module) -> None:
    db = newsletter_db_module
    contact = db.add_contact(
        email="client@boulangerie.fr",
        name="Jean Dupont",
        sector="boulangerie",
        company="Le Fournil",
    )
    assert contact["subscribed"] is True

    found = db.get_contact_by_email("CLIENT@boulangerie.fr")
    assert found is not None
    assert found["id"] == contact["id"]

    seq = db.create_sequence(contact["id"], "project_delivered")
    assert seq["status"] == "pending"

    email = db.add_email(
        type="welcome_j0",
        subject="Bienvenue",
        html_content="<p>Bonjour</p>",
        sequence_id=seq["id"],
        contact_id=contact["id"],
        status="scheduled",
        scheduled_at="2000-01-01T00:00:00+00:00",
    )
    assert email["type"] == "welcome_j0"

    pending = db.list_pending_emails()
    assert any(e["id"] == email["id"] for e in pending)

    updated = db.update_email(
        email["id"],
        status="sent",
        sent_at="2026-01-01T00:00:00+00:00",
        brevo_message_id="msg-123",
    )
    assert updated is not None
    assert updated["status"] == "sent"
    assert db.list_pending_emails() == []
