"""Tests API newsletter — routes mockées."""

from __future__ import annotations

import asyncio
import importlib
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def newsletter_client(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "newsletter_api.db"
        import cockpit_db

        importlib.reload(cockpit_db)
        monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
        cockpit_db.init_db()

        import newsletter_db
        import newsletter_router

        importlib.reload(newsletter_db)
        importlib.reload(newsletter_router)

        from api.main import create_app

        app = create_app()
        app.include_router(newsletter_router.router, prefix="/api/newsletter")
        with TestClient(app) as client:
            yield client


def test_contacts_crud(newsletter_client: TestClient) -> None:
    created = newsletter_client.post(
        "/api/newsletter/contacts",
        json={"name": "Jean", "email": "jean@test.fr", "sector": "boulangerie"},
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    listed = newsletter_client.get("/api/newsletter/contacts")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    deleted = newsletter_client.delete(f"/api/newsletter/contacts/{cid}")
    assert deleted.status_code == 204


def test_webhook_new_prospect(newsletter_client: TestClient) -> None:
    fake_emails = [
        {
            "id": "e1",
            "type": "welcome_j0",
            "sequence_id": "s1",
            "contact_id": "c1",
            "subject": "Bienvenue",
            "html_content": "<p>Hi</p>",
            "status": "scheduled",
        },
        {
            "id": "e2",
            "type": "welcome_j1",
            "sequence_id": "s1",
            "contact_id": "c1",
            "subject": "J1",
            "html_content": "<p>J1</p>",
            "status": "scheduled",
        },
        {
            "id": "e3",
            "type": "welcome_j3",
            "sequence_id": "s1",
            "contact_id": "c1",
            "subject": "J3",
            "html_content": "<p>J3</p>",
            "status": "scheduled",
        },
    ]

    with (
        patch(
            "newsletter_router.agent.generate_welcome_sequence",
            new=AsyncMock(return_value=fake_emails),
        ),
        patch(
            "newsletter_router._send_newsletter_email_row",
            new=AsyncMock(return_value={"sent": True, "email_id": "e1"}),
        ),
    ):
        resp = newsletter_client.post(
            "/api/newsletter/webhook/new-prospect",
            json={
                "name": "Marie",
                "email": "marie@corp.fr",
                "company": "Corp",
                "sector": "ecommerce",
                "message": "Intéressée par CyberForge",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["emails_scheduled"] == 3
    assert data["j0_sent"] is True


def test_send_pending(newsletter_client: TestClient) -> None:
    import newsletter_db as db

    contact = db.add_contact(email="pending@test.fr", name="Pending")
    row = db.add_email(
        type="welcome_j1",
        subject="Test",
        html_content="<p>x</p>",
        contact_id=contact["id"],
        status="scheduled",
        scheduled_at="2000-01-01T00:00:00+00:00",
    )

    with patch(
        "newsletter_router.send_html_email",
        new=AsyncMock(return_value="brevo-123"),
    ):
        resp = newsletter_client.post("/api/newsletter/send-pending")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] >= 1
    updated = db.get_email(row["id"])
    assert updated is not None
    assert updated["status"] == "sent"
