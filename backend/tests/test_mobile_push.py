"""Tests API mobile — push tokens et health."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from api.routes import mobile as mobile_routes


def test_register_push_token_and_health() -> None:
    mobile_routes.push_tokens.clear()
    client = TestClient(create_app())

    res = client.post(
        "/api/mobile/register-push-token",
        json={"token": "ExponentPushToken[test-token]", "platform": "android"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["registered"] == 1

    health = client.get("/api/mobile/health")
    assert health.status_code == 200
    data = health.json()
    assert data["status"] == "ok"
    assert data["tokens"] == 1

    dup = client.post(
        "/api/mobile/register-push-token",
        json={"token": "ExponentPushToken[test-token]", "platform": "android"},
    )
    assert dup.json()["registered"] == 1
