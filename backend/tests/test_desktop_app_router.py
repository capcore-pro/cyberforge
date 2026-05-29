"""Tests desktop_app_router — commandes et statut."""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def desktop_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "desktop_router.db"
    monkeypatch.setattr("cockpit_db._DB_PATH", db_path)

    import cockpit_db
    import desktop_app_db
    import desktop_app_router

    importlib.reload(cockpit_db)
    importlib.reload(desktop_app_db)
    importlib.reload(desktop_app_router)
    cockpit_db.init_db()

    app = FastAPI()
    app.include_router(desktop_app_router.router, prefix="/api/desktop")
    return TestClient(app), desktop_app_db


def test_create_order_and_status(desktop_client) -> None:
    client, db = desktop_client
    fake_session = type("S", (), {"id": "cs_test_123", "url": "https://checkout.stripe.test/x"})()

    with patch(
        "desktop_app_router.create_desktop_checkout_session",
        return_value=fake_session,
    ):
        response = client.post(
            "/api/desktop/orders",
            json={
                "app_type": "facture_express",
                "client_email": "client@example.com",
                "client_name": "Dupont",
                "price_cents": 1900,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["order_id"]
    assert payload["checkout_url"] == "https://checkout.stripe.test/x"

    status = client.get(f"/api/desktop/orders/{payload['order_id']}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["generation_status"] == "waiting"
    assert body["r2_url"] is None


def test_webhook_triggers_generation(desktop_client) -> None:
    client, db = desktop_client
    order = db.create_order(
        app_type="lead_tracker",
        client_email="a@b.com",
        stripe_session_id="cs_webhook_1",
    )

    with patch("desktop_app_router.verify_desktop_webhook_signature", return_value=True):
        with patch("desktop_app_router._spawn_generate_exe") as spawn:
            response = client.post(
                "/api/desktop/webhook/stripe",
                content=b'{"type":"checkout.session.completed","data":{"object":{"id":"cs_webhook_1"}}}}',
                headers={"Stripe-Signature": "t=1,v1=test"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    spawn.assert_called_once_with(order["id"])

    updated = db.get_order(order["id"])
    assert updated is not None
    assert updated["stripe_payment_status"] == "paid"
