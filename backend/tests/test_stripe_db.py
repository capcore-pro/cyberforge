"""Tests stripe_db — configs, transactions, abonnements."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def stripe_db_module(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "stripe_test.db"
    monkeypatch.setattr("cockpit_db._DB_PATH", db_path)

    import cockpit_db
    import stripe_db

    importlib.reload(cockpit_db)
    importlib.reload(stripe_db)
    cockpit_db.init_db()
    yield stripe_db


def test_stripe_config_transaction_subscription(stripe_db_module) -> None:
    db = stripe_db_module
    cfg = db.add_config(
        project_id="proj-1",
        project_name="Boutique test",
        publishable_key="pk_test_xxx",
        secret_key="sk_test_xxx",
        webhook_secret="whsec_test",
    )
    assert cfg["enabled"] is True
    assert db.decrypt_config_secret(cfg["secret_key_encrypted"]) == "sk_test_xxx"

    tx = db.add_transaction(
        stripe_config_id=cfg["id"],
        project_id="proj-1",
        stripe_payment_intent_id="pi_123",
        amount_eur=49.0,
        type="one_shot",
        status="paid",
        customer_email="client@example.com",
    )
    assert tx["status"] == "paid"

    sub = db.add_subscription(
        stripe_config_id=cfg["id"],
        project_id="proj-1",
        stripe_subscription_id="sub_123",
        customer_email="client@example.com",
        plan_name="Pro",
        amount_eur=29.0,
    )
    assert db.get_subscription("sub_123") is not None

    assert len(db.list_transactions(project_id="proj-1")) == 1
    assert len(db.list_subscriptions(project_id="proj-1", status="active")) == 1

    assert db.delete_config(cfg["id"]) is True
    assert db.list_transactions(project_id="proj-1") == []
