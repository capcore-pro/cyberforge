"""Tests legal_generator — PDF ReportLab."""

from __future__ import annotations

import importlib
import uuid
from pathlib import Path

import pytest

reportlab = pytest.importorskip("reportlab")


@pytest.fixture()
def legal_stack(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_path = tmp_path / "legal_gen.db"
    docs_root = tmp_path / "documents"
    monkeypatch.setenv("LEGAL_DOCUMENTS_ROOT", str(docs_root))
    monkeypatch.setenv("MAT_SIRET", "12345678901234")

    import cockpit_db
    import legal_db
    import legal_generator
    from config import refresh_settings

    refresh_settings()
    importlib.reload(cockpit_db)
    importlib.reload(legal_db)
    importlib.reload(legal_generator)
    monkeypatch.setattr(cockpit_db, "_DB_PATH", db_path)
    cockpit_db.init_db()
    yield legal_generator, legal_db, docs_root


def test_generate_devis_and_facture(legal_stack) -> None:
    gen, db, docs_root = legal_stack
    client = db.add_client(name="Client PDF", email="pdf@test.fr")
    devis = db.create_document(
        type="devis",
        title="Site vitrine test",
        client_id=client["id"],
        number=f"DEV-TEST-{uuid.uuid4().hex[:8]}",
    )
    db.add_line_item(
        document_id=devis["id"],
        description="Développement",
        quantity=1,
        unit_price=1500.0,
    )

    path = gen.generate_devis(devis["id"])
    assert Path(path).is_file()
    assert Path(path).suffix == ".pdf"
    assert docs_root.joinpath("devis").exists()

    updated = db.get_document(devis["id"])
    assert updated is not None
    assert updated["pdf_path"] == path

    facture = db.create_document(
        type="facture",
        title="Site vitrine test",
        client_id=client["id"],
        number=f"FAC-TEST-{uuid.uuid4().hex[:8]}",
        status="paid",
    )
    db.add_line_item(
        document_id=facture["id"],
        description="Solde",
        quantity=1,
        unit_price=1500.0,
    )
    fac_path = gen.generate_facture(facture["id"])
    assert Path(fac_path).is_file()
    assert Path(fac_path).stat().st_size > 500


def test_generate_cgv_and_mentions(legal_stack) -> None:
    gen, db, docs_root = legal_stack
    cgv_path = gen.generate_cgv()
    assert Path(cgv_path).is_file()
    assert (docs_root / "cgv").exists()

    ml_path = gen.generate_mentions_legales("proj-test-uuid")
    assert Path(ml_path).is_file()
    assert (docs_root / "mentions_legales").exists()

    docs = db.list_documents(type="mentions_legales", limit=10)
    assert any(d.get("project_id") == "proj-test-uuid" for d in docs)
