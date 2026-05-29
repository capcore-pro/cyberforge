"""Tests API cockpit — topup, seuils, alertes."""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def cockpit_client(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cockpit_test.db"
        monkeypatch.setattr("cockpit_db._DB_PATH", db_path)

        import cockpit_db

        importlib.reload(cockpit_db)
        cockpit_db.init_db()

        import cockpit_router

        importlib.reload(cockpit_router)

        from api.main import create_app

        application = create_app()
        application.include_router(
            cockpit_router.router,
            prefix="/api/cockpit",
        )
        with TestClient(application) as client:
            yield client, cockpit_db


def test_topup_creates_alert_when_below_threshold(
    cockpit_client: tuple[TestClient, object],
) -> None:
    client, db = cockpit_client
    sid = db.add_service(
        name="Alert Test",
        api_key_env="ALERT_TEST_KEY",
        connector="manual",
        service_id="alert-test-svc",
    )
    db.set_thresholds(sid, warning_eur=100.0, critical_eur=50.0, urgent_eur=10.0)
    db.set_balance(sid, 8.0)

    resp = client.post(
        f"/api/cockpit/services/{sid}/topup",
        json={"amount_eur": 1.0, "description": "petit topup"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["alerts_created"]) >= 1
    assert data["alerts_created"][0]["level"] == "urgent"

    alerts = client.get("/api/cockpit/alerts")
    assert alerts.status_code == 200
    assert len(alerts.json()) >= 1


def test_topup_rejects_non_positive_amount(
    cockpit_client: tuple[TestClient, object],
) -> None:
    client, db = cockpit_client
    sid = db.add_service(
        name="Validate",
        api_key_env="VALIDATE_KEY",
        connector="manual",
        service_id="validate-topup",
    )
    resp = client.post(
        f"/api/cockpit/services/{sid}/topup",
        json={"amount_eur": 0},
    )
    assert resp.status_code == 422


def test_dashboard_and_mark_alerts_read(
    cockpit_client: tuple[TestClient, object],
) -> None:
    client, _cockpit_client = cockpit_client
    dash = client.get("/api/cockpit/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert "services" in body
    assert "expenses" in body
    assert "month_total_eur" in body

    read_resp = client.post("/api/cockpit/alerts/read", json={})
    assert read_resp.status_code == 200
    assert read_resp.json()["marked_read"] >= 0


def test_sync_manual_service(
    cockpit_client: tuple[TestClient, object],
) -> None:
    client, db = cockpit_client
    sid = db.add_service(
        name="Sync Manual",
        api_key_env="SYNC_MANUAL_KEY",
        connector="manual",
        service_id="sync-manual-svc",
    )
    db.set_balance(sid, 25.0)
    resp = client.post(f"/api/cockpit/services/{sid}/sync")
    assert resp.status_code == 200
    assert resp.json()["balance_eur"] == 25.0
