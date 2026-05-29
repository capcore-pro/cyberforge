"""Tests API legal — clients, documents, PDF."""

from __future__ import annotations

import importlib
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

reportlab = pytest.importorskip("reportlab")


@pytest.fixture()
def legal_client(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "legal_api.db"
        docs_root = Path(tmp) / "documents"
        monkeypatch.setenv("LEGAL_DOCUMENTS_ROOT", str(docs_root))
        monkeypatch.setenv("MAT_SIRET", "12345678901234")

        import cockpit_db

        importlib.reload(cockpit_db)
        monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
        cockpit_db.init_db()

        import legal_db
        import legal_router

        importlib.reload(legal_db)
        importlib.reload(legal_router)

        from api.main import create_app

        app = create_app()
        app.include_router(legal_router.router, prefix="/api/legal")
        with TestClient(app) as client:
            yield client, docs_root


def test_clients_crud(legal_client: tuple[TestClient, Path]) -> None:
    client, _ = legal_client
    created = client.post(
        "/api/legal/clients",
        json={"name": "Test SARL", "email": "test@example.com"},
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    listed = client.get("/api/legal/clients")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    updated = client.put(
        f"/api/legal/clients/{cid}",
        json={"phone": "+33 6 00 00 00 00"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+33 6 00 00 00 00"

    deleted = client.delete(f"/api/legal/clients/{cid}")
    assert deleted.status_code == 204


def test_document_with_lines_and_pdf(legal_client: tuple[TestClient, Path]) -> None:
    client, docs_root = legal_client
    cl = client.post(
        "/api/legal/clients",
        json={"name": "Client PDF", "email": "pdf@client.fr"},
    ).json()

    doc_resp = client.post(
        "/api/legal/documents",
        json={
            "type": "devis",
            "title": "Site test",
            "client_id": cl["id"],
            "line_items": [
                {
                    "description": "Développement site",
                    "quantity": 1,
                    "unit_price": 2000,
                }
            ],
        },
    )
    assert doc_resp.status_code == 201
    doc = doc_resp.json()
    assert doc["total_ht"] == 2000.0
    assert len(doc["line_items"]) == 1

    gen = client.post(f"/api/legal/documents/{doc['id']}/generate-pdf")
    assert gen.status_code == 200
    assert gen.json()["pdf_path"]
    assert "/api/legal/documents/" in gen.json()["pdf_url"]

    pdf_get = client.get(f"/api/legal/documents/{doc['id']}/pdf")
    assert pdf_get.status_code == 200
    assert pdf_get.headers["content-type"] == "application/pdf"


def test_status_update(legal_client: tuple[TestClient, Path]) -> None:
    client, _ = legal_client
    doc = client.post(
        "/api/legal/documents",
        json={"type": "facture", "title": "Facture test"},
    ).json()
    resp = client.put(
        f"/api/legal/documents/{doc['id']}/status",
        json={"status": "paid"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@patch(
    "legal_router.send_document_email_to_client",
    new_callable=AsyncMock,
    return_value=True,
)
def test_send_document(mock_send, legal_client: tuple[TestClient, Path]) -> None:
    client, _ = legal_client
    cl = client.post(
        "/api/legal/clients",
        json={"name": "Dest", "email": "dest@test.fr"},
    ).json()
    doc = client.post(
        "/api/legal/documents",
        json={
            "type": "devis",
            "title": "Envoi test",
            "client_id": cl["id"],
            "line_items": [{"description": "Ligne", "quantity": 1, "unit_price": 100}],
        },
    ).json()
    client.post(f"/api/legal/documents/{doc['id']}/generate-pdf")

    sent = client.post(
        f"/api/legal/documents/{doc['id']}/send",
        json={"message": "Merci pour votre confiance."},
    )
    assert sent.status_code == 200
    assert sent.json()["sent"] is True
    mock_send.assert_awaited_once()

    updated = client.get("/api/legal/documents", params={"status": "sent"})
    assert any(d["id"] == doc["id"] for d in updated.json())


@patch("legal_router._fetch_project_row", new_callable=AsyncMock)
def test_from_project_prefill(mock_project, legal_client: tuple[TestClient, Path]) -> None:
    client, _ = legal_client
    pid = str(uuid.uuid4())
    mock_project.return_value = {
        "id": pid,
        "title": "Boulangerie Demo",
        "prompt": "Site vitrine boulangerie artisanale",
        "project_type": "site_web",
        "summary": None,
    }

    with patch("legal_router.build_costs_api_response") as mock_costs:
        mock_costs.return_value = {
            "architect_plan": {"suggested_price_min": 2400},
        }
        resp = client.post(f"/api/legal/documents/from-project/{pid}")

    assert resp.status_code == 201
    data = resp.json()
    assert "Création Site web" in data["title"]
    assert data["project_id"] == pid
    assert data["client_id"] is None
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["unit_price"] == 2400.0
