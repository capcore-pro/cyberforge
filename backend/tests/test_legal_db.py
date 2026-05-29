"""Tests legal_db — clients, documents, lignes."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def legal_db_module(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "legal_test.db"
        import cockpit_db
        import legal_db

        importlib.reload(cockpit_db)
        importlib.reload(legal_db)
        monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
        cockpit_db.init_db()
        yield legal_db


def test_client_crud(legal_db_module) -> None:
    db = legal_db_module
    client = db.add_client(
        name="Boulangerie Le Fournil",
        email="contact@fournil.fr",
        siret="12345678901234",
    )
    assert client["name"] == "Boulangerie Le Fournil"

    updated = db.update_client(client["id"], phone="+33 1 23 45 67 89")
    assert updated is not None
    assert updated["phone"] == "+33 1 23 45 67 89"

    listed = db.list_clients()
    assert len(listed) == 1
    assert db.delete_client(client["id"])


def test_document_numbering_and_line_items(legal_db_module) -> None:
    db = legal_db_module
    n1 = db.next_document_number("devis")
    assert n1.endswith("-001")

    client = db.add_client(name="Client Test", email="a@b.fr")
    doc = db.create_document(
        type="devis",
        title="Création site vitrine",
        client_id=client["id"],
        number=n1,
        tva_rate=0,
    )
    assert doc["number"] == n1
    n2 = db.next_document_number("devis")
    assert n2.endswith("-002")
    assert doc["status"] == "draft"

    line = db.add_line_item(
        document_id=doc["id"],
        description="Site vitrine Next.js",
        quantity=1,
        unit_price=2400.0,
    )
    assert line["total"] == 2400.0

    refreshed = db.get_document(doc["id"])
    assert refreshed is not None
    assert refreshed["total_ht"] == 2400.0
    assert refreshed["total_ttc"] == 2400.0

    items = db.get_line_items(doc["id"])
    assert len(items) == 1

    assert db.delete_document(doc["id"])
    assert db.get_line_items(doc["id"]) == []
