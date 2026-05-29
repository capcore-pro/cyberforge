"""Tests stripe_service — résolution de contexte et dashboard."""

from __future__ import annotations

import importlib
import uuid
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def stripe_service_module(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "stripe_svc.db"
    monkeypatch.setattr("cockpit_db._DB_PATH", db_path)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_capcore")

    import cockpit_db
    import stripe_db
    import stripe_service

    importlib.reload(cockpit_db)
    importlib.reload(stripe_db)
    importlib.reload(stripe_service)
    cockpit_db.init_db()
    yield stripe_service


def test_resolve_context_uses_capcore_fallback(stripe_service_module) -> None:
    svc = stripe_service_module
    ctx = svc._resolve_context(None)
    assert ctx.project_id == "capcore"
    assert ctx.api_key == "sk_test_capcore"


def test_get_dashboard_data_empty(stripe_service_module) -> None:
    svc = stripe_service_module
    data = svc.get_dashboard_data()
    assert data["total_collected_eur"] == 0.0
    assert data["active_subscriptions_count"] == 0


def test_create_checkout_session_calls_stripe(stripe_service_module) -> None:
    svc = stripe_service_module
    db = importlib.import_module("stripe_db")

    project_id = f"boutique-{uuid.uuid4().hex[:8]}"
    db.add_config(
        project_id=project_id,
        project_name="Boutique",
        publishable_key="pk_test",
        secret_key="sk_test_client",
    )

    fake_session = MagicMock()
    fake_session.id = "cs_test_1"
    fake_session.url = "https://checkout.stripe.test/cs_test_1"
    fake_session.payment_intent = "pi_test_1"

    with patch.object(svc.stripe.checkout.Session, "create", return_value=fake_session):
        session = svc.create_checkout_session(
            project_id=project_id,
            items=[{"name": "Produit", "amount_eur": 10.0}],
            customer_email="buyer@example.com",
            success_url="https://example.com/ok",
            cancel_url="https://example.com/cancel",
        )

    assert session.id == "cs_test_1"
    txs = db.list_transactions(project_id=project_id)
    assert len(txs) == 1
    assert txs[0]["status"] == "pending"
