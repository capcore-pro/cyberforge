"""Tests stripe_router — configs et dashboard."""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def stripe_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "stripe_router.db"
    monkeypatch.setattr("cockpit_db._DB_PATH", db_path)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_capcore")

    import cockpit_db
    import stripe_db
    import stripe_router

    importlib.reload(cockpit_db)
    importlib.reload(stripe_db)
    importlib.reload(stripe_router)
    cockpit_db.init_db()

    app = FastAPI()
    app.include_router(stripe_router.router, prefix="/api/stripe")
    return TestClient(app), stripe_db


def test_configs_crud(stripe_client) -> None:
    client, db = stripe_client

    created = client.post(
        "/api/stripe/configs",
        json={
            "project_id": "p1",
            "project_name": "Projet 1",
            "publishable_key": "pk_test",
            "secret_key": "sk_test",
            "webhook_secret": "whsec_test",
        },
    )
    assert created.status_code == 201
    cfg_id = created.json()["id"]
    assert created.json()["secret_key_encrypted"] == "***"

    listed = client.get("/api/stripe/configs")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    updated = client.put(
        f"/api/stripe/configs/{cfg_id}",
        json={"project_name": "Projet un"},
    )
    assert updated.status_code == 200
    assert updated.json()["project_name"] == "Projet un"

    deleted = client.delete(f"/api/stripe/configs/{cfg_id}")
    assert deleted.status_code == 200


def test_dashboard_empty(stripe_client) -> None:
    client, _ = stripe_client
    response = client.get("/api/stripe/dashboard")
    assert response.status_code == 200
    assert response.json()["total_collected_eur"] == 0.0
