"""Tests Mode Client — statuts démos et normalisation."""

from db.clients_store import MANUAL_DEMO_STATUSES, _normalize_kind
from db.demos_store import _normalize_status, replace_row_open, DemoRow, DemoPayload


def test_normalize_client_kind() -> None:
    assert _normalize_kind(True) == "perso"
    assert _normalize_kind("perso") == "perso"
    assert _normalize_kind(False) == "client"
    assert _normalize_kind("client") == "client"


def test_normalize_demo_status() -> None:
    assert _normalize_status("ouverte") == "ouverte"
    assert _normalize_status("invalid") == "envoyee"


def test_manual_statuses_subset() -> None:
    assert "validee" in MANUAL_DEMO_STATUSES
    assert "expiree" in MANUAL_DEMO_STATUSES
    assert "ouverte" not in MANUAL_DEMO_STATUSES


def test_replace_row_open() -> None:
    row = DemoRow(
        id="1",
        token="tok",
        title="T",
        expires_at="2099-01-01T00:00:00+00:00",
        duration_hours=24,
        payload=DemoPayload(preview_html="<html></html>"),
        status="envoyee",
        created_at="2026-01-01T00:00:00+00:00",
    )
    updated = replace_row_open(row, "2026-05-01T12:00:00+00:00")
    assert updated.status == "ouverte"
    assert updated.opened_at == "2026-05-01T12:00:00+00:00"
