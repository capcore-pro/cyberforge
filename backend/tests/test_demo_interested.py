"""Tests statut intéressé + injection runtime démo."""

from unittest.mock import AsyncMock, MagicMock, patch

from tools.capcore_notify import _build_contact_email
from tools.demo_password_vault import decrypt_demo_password, encrypt_demo_password

import asyncio

from fastapi.testclient import TestClient

from api.main import create_app
from db.demos_store import DemoPayload, DemoRow
from tools.demo_runtime import inject_demo_runtime_config


def _sample_row(*, status: str = "ouverte") -> DemoRow:
    return DemoRow(
        id="id-1",
        token="tok-demo",
        title="Projet CRM",
        expires_at="2099-01-01T00:00:00Z",
        duration_hours=24,
        payload=DemoPayload(preview_html="<html></html>"),
        status=status,  # type: ignore[arg-type]
        created_at="2026-01-01T00:00:00Z",
    )


def test_demo_password_vault_roundtrip() -> None:
    enc = encrypt_demo_password("Secret42!")
    assert decrypt_demo_password(enc) == "Secret42!"


def test_capcore_contact_email_subject_and_body() -> None:
    subject, body = _build_contact_email(
        project_title="CRM Acme",
        client_name="Jean",
        client_email="jean@acme.fr",
        message="On veut une démo live",
        demo_url="https://cyberforge-demos.pages.dev/d/tok",
        demo_password="pass-demo",
        unlock_url="http://localhost:5173/demo/tok",
    )
    assert subject == "🔔 Nouveau contact — CRM Acme"
    assert "Jean" in body
    assert "pass-demo" in body
    assert "cyberforge-demos.pages.dev" in body


def test_inject_demo_runtime_config_adds_json_script() -> None:
    html = inject_demo_runtime_config(
        "<!DOCTYPE html><html><body><p>Hi</p></body></html>",
        token="abc123",
        project_title="Mon CRM",
        demo_url="https://cyberforge-demos.pages.dev/d/abc123",
        api_base_url="https://api.example.com",
    )
    assert 'id="cf-demo-runtime"' in html
    assert "Mon CRM" in html
    assert "abc123" in html
    assert "https://api.example.com" in html
    assert html.index("cf-demo-runtime") < html.lower().index("</body>")


def test_premium_html_submits_contact_via_post() -> None:
    from tools.demo_template_service import build_html_from_seed, heuristic_demo_seed

    seed = heuristic_demo_seed("CRM test", project_type_label="SaaS")
    html = build_html_from_seed(seed)
    assert "submitDemoContact" in html
    assert 'method: "POST"' in html or "method: \"POST\"" in html


def test_record_interested_updates_status() -> None:
    from db.demos_store import DemosStore

    store = DemosStore.__new__(DemosStore)
    store._supabase = MagicMock()
    row = _sample_row()

    with (
        patch.object(store, "get_by_token", new_callable=AsyncMock, return_value=row),
        patch.object(store, "is_expired", return_value=False),
        patch.object(store, "_rest_url", return_value="https://example.supabase.co/rest/v1"),
        patch("db.demos_store.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "id": row.id,
                "token": row.token,
                "title": row.title,
                "expires_at": row.expires_at,
                "duration_hours": row.duration_hours,
                "payload": {},
                "status": "interessee",
                "created_at": row.created_at,
            }
        ]
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.patch = AsyncMock(return_value=mock_resp)

        from db.demos_store import InterestContact

        updated = asyncio.run(
            DemosStore.record_interested(
                store,
                "tok-demo",
                contact=InterestContact(
                    name="Alice",
                    email="alice@example.com",
                    message="Bonjour",
                ),
            )
        )

    assert updated is not None
    assert updated.status == "interessee"


def test_submit_demo_interested_post_route() -> None:
    app = create_app()
    row = _sample_row()
    updated = row.model_copy(update={"status": "interessee"})  # type: ignore[arg-type]

    with (
        patch("api.routes.demos.get_demos_store") as mock_get_store,
        patch(
            "api.routes.demos.send_capcore_contact_email",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_mail,
    ):
        store = mock_get_store.return_value
        store.is_configured.return_value = True
        store.get_by_token = AsyncMock(return_value=row)
        store.is_expired.return_value = False
        store.record_interested = AsyncMock(return_value=updated)

        client = TestClient(app)
        resp = client.post(
            "/api/demos/tok-demo/interested",
            json={
                "name": "Bob",
                "email": "bob@test.com",
                "message": "Je suis intéressé",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "interessee"
    assert data["recorded"] is True
    assert data["email_sent"] is True
    mock_mail.assert_awaited_once()


def test_track_demo_interested_route() -> None:
    app = create_app()
    row = _sample_row()
    updated = row.model_copy(update={"status": "interessee"})  # type: ignore[arg-type]

    with patch("api.routes.demos.get_demos_store") as mock_get_store:
        store = mock_get_store.return_value
        store.is_configured.return_value = True
        store.get_by_token = AsyncMock(return_value=row)
        store.is_expired.return_value = False
        store.record_interested = AsyncMock(return_value=updated)

        client = TestClient(app)
        resp = client.get("/api/demos/tok-demo/interested")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "interessee"
    assert data["recorded"] is True
