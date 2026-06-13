"""Tests Pipeline Commercial — store + API."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.prospect_store import STATUTS, ProspectStore


def test_move_statut_sets_contact_and_closed_dates() -> None:
    store = ProspectStore(supabase=MagicMock())
    store.is_configured = MagicMock(return_value=True)
    store.update = AsyncMock(return_value={"id": "p1", "statut": "contacté"})

    asyncio.run(store.move_statut("p1", "contacté"))
    call_args = store.update.await_args
    assert call_args is not None
    updates = call_args.args[1]
    assert updates["statut"] == "contacté"
    assert "contact_date" in updates

    store.update.reset_mock()
    asyncio.run(store.move_statut("p1", "gagné"))
    updates = store.update.await_args.args[1]
    assert "closed_date" in updates


def test_get_stats_aggregates_by_statut() -> None:
    store = ProspectStore(supabase=MagicMock())
    store.list_all = AsyncMock(
        return_value=[
            {
                "statut": "nouveau",
                "valeur_estimee": 1000,
                "created_at": "2026-06-10T10:00:00+00:00",
            },
            {
                "statut": "gagné",
                "valeur_estimee": 5000,
                "created_at": "2026-06-01T10:00:00+00:00",
            },
            {
                "statut": "perdu",
                "valeur_estimee": 2000,
                "created_at": "2026-06-05T10:00:00+00:00",
            },
        ]
    )

    stats = asyncio.run(store.get_stats())
    assert stats["total_prospects"] == 3
    assert stats["par_statut"]["nouveau"]["count"] == 1
    assert stats["par_statut"]["gagné"]["count"] == 1
    assert stats["taux_conversion"] == pytest.approx(33.3, abs=0.1)
    assert stats["valeur_pipeline"] == 6000


def test_create_list_delete_prospect_api() -> None:
    store = MagicMock()
    store.is_configured.return_value = True
    store.create = AsyncMock(
        return_value={
            "id": "prospect-1",
            "nom": "Alice Martin",
            "statut": "nouveau",
            "valeur_estimee": 1500,
            "created_at": "2026-06-10T10:00:00",
            "updated_at": "2026-06-10T10:00:00",
        }
    )
    store.list_all = AsyncMock(
        return_value=[
            {
                "id": "prospect-1",
                "nom": "Alice Martin",
                "statut": "nouveau",
                "valeur_estimee": 1500,
            }
        ]
    )
    store.move_statut = AsyncMock(
        return_value={
            "id": "prospect-1",
            "nom": "Alice Martin",
            "statut": "contacté",
            "updated_at": "2026-06-10T11:00:00",
        }
    )
    store.delete = AsyncMock(return_value=True)
    store.get_stats = AsyncMock(
        return_value={
            "par_statut": {"nouveau": {"count": 0, "valeur": 0}},
            "total_prospects": 0,
            "valeur_pipeline": 0,
            "taux_conversion": 0,
            "prospects_ce_mois": 0,
        }
    )

    with patch("api.routes.pipeline.get_prospect_store", return_value=store):
        client = TestClient(create_app())

        create_res = client.post(
            "/api/pipeline/prospects",
            json={"nom": "Alice Martin", "valeur_estimee": 1500},
        )
        assert create_res.status_code == 200, create_res.text
        assert create_res.json()["statut"] == "nouveau"

        list_res = client.get("/api/pipeline/prospects")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        move_res = client.patch(
            "/api/pipeline/prospects/prospect-1/statut",
            json={"statut": "contacté"},
        )
        assert move_res.status_code == 200
        assert move_res.json()["statut"] == "contacté"

        del_res = client.delete("/api/pipeline/prospects/prospect-1")
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True


def test_stats_api_route() -> None:
    store = MagicMock()
    store.is_configured.return_value = True
    store.get_stats = AsyncMock(
        return_value={
            "par_statut": {
                "nouveau": {"count": 2, "valeur": 3000},
                "contacté": {"count": 1, "valeur": 1200},
            },
            "total_prospects": 3,
            "valeur_pipeline": 4200,
            "taux_conversion": 0,
            "prospects_ce_mois": 2,
        }
    )

    with patch("api.routes.pipeline.get_prospect_store", return_value=store):
        client = TestClient(create_app())
        res = client.get("/api/pipeline/stats")

    assert res.status_code == 200
    data = res.json()
    assert data["total_prospects"] == 3
    assert data["par_statut"]["nouveau"]["count"] == 2


def test_statuts_list_complete() -> None:
    assert len(STATUTS) == 6
    assert "démo_envoyée" in STATUTS
