"""
Module juridique / commercial — clients, devis, factures (cockpit.db).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now

DocumentType = Literal["devis", "facture", "mentions_legales", "cgv"]
DocumentStatus = Literal["draft", "sent", "signed", "paid", "cancelled"]

_DOCUMENT_TYPES = frozenset({"devis", "facture", "mentions_legales", "cgv"})
_DOCUMENT_STATUSES = frozenset({"draft", "sent", "signed", "paid", "cancelled"})
_NUMBER_PREFIX: dict[str, str] = {
    "devis": "DEVIS",
    "facture": "FACTURE",
    "mentions_legales": "ML",
    "cgv": "CGV",
}


def init_legal_db() -> None:
    """Crée les tables clients, documents et line_items."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    siret TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL CHECK (
                        type IN ('devis', 'facture', 'mentions_legales', 'cgv')
                    ),
                    number TEXT NOT NULL,
                    client_id TEXT,
                    project_id TEXT,
                    status TEXT NOT NULL DEFAULT 'draft' CHECK (
                        status IN ('draft', 'sent', 'signed', 'paid', 'cancelled')
                    ),
                    title TEXT NOT NULL,
                    notes TEXT,
                    total_ht REAL NOT NULL DEFAULT 0,
                    tva_rate REAL NOT NULL DEFAULT 0,
                    total_ttc REAL NOT NULL DEFAULT 0,
                    pdf_path TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS line_items (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 1,
                    unit_price REAL NOT NULL DEFAULT 0,
                    total REAL NOT NULL DEFAULT 0,
                    "order" INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_clients_name
                    ON clients (name COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_documents_type_created
                    ON documents (type, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_client
                    ON documents (client_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_status
                    ON documents (status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_line_items_document_order
                    ON line_items (document_id, "order" ASC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_number
                    ON documents (number);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _compute_ttc(total_ht: float, tva_rate: float) -> float:
    rate = max(0.0, float(tva_rate))
    return _round_money(float(total_ht) * (1.0 + rate / 100.0))


def _recalc_document_totals(conn: sqlite3.Connection, document_id: str) -> None:
    exists = conn.execute(
        "SELECT 1 FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    if exists is None:
        return
    sum_row = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM line_items WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    total_ht = _round_money(float(sum_row[0] if sum_row else 0))
    tva_rate = float(
        conn.execute(
            "SELECT tva_rate FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()[0]
    )
    total_ttc = _compute_ttc(total_ht, tva_rate)
    conn.execute(
        """
        UPDATE documents
        SET total_ht = ?, total_ttc = ?
        WHERE id = ?
        """,
        (total_ht, total_ttc, document_id),
    )


# --- Clients ---


def add_client(
    *,
    name: str,
    email: str,
    phone: str | None = None,
    address: str | None = None,
    siret: str | None = None,
    client_id: str | None = None,
) -> dict[str, Any]:
    clean_name = name.strip()
    clean_email = email.strip()
    if not clean_name:
        raise ValueError("name est requis.")
    if not clean_email:
        raise ValueError("email est requis.")

    cid = (client_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO clients (id, name, email, phone, address, siret, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    clean_name,
                    clean_email,
                    phone.strip() if phone else None,
                    address.strip() if address else None,
                    siret.strip() if siret else None,
                    now,
                ),
            )
            conn.commit()
            return _row_to_dict(
                conn.execute("SELECT * FROM clients WHERE id = ?", (cid,)).fetchone()
            )  # type: ignore[return-value]
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Client déjà existant : {cid}") from exc
        finally:
            conn.close()


def get_client(client_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?",
                (client_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_clients(*, limit: int = 500) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 2000))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM clients
                ORDER BY name COLLATE NOCASE
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def update_client(client_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"name", "email", "phone", "address", "siret"}
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if isinstance(value, str):
            updates[key] = value.strip() if value else value
        else:
            updates[key] = value

    if not updates:
        return get_client(client_id)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [client_id.strip()]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE clients SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?",
                (client_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def delete_client(client_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM clients WHERE id = ?", (client_id.strip(),))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- Documents ---


def next_document_number(doc_type: DocumentType) -> str:
    """Génère le prochain numéro séquentiel (ex. DEV-2026-001)."""
    kind = doc_type.strip().lower()
    if kind not in _DOCUMENT_TYPES:
        raise ValueError("type document invalide.")

    prefix = _NUMBER_PREFIX[kind]
    year = datetime.now(timezone.utc).year
    pattern = f"{prefix}-{year}-%"

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT number FROM documents
                WHERE type = ? AND number LIKE ?
                """,
                (kind, pattern),
            ).fetchall()
        finally:
            conn.close()

    max_seq = 0
    for row in rows:
        num = str(row[0])
        part = num.rsplit("-", 1)[-1]
        try:
            max_seq = max(max_seq, int(part))
        except ValueError:
            continue

    return f"{prefix}-{year}-{max_seq + 1:03d}"


def create_document(
    *,
    type: DocumentType,
    title: str,
    number: str | None = None,
    client_id: str | None = None,
    project_id: str | None = None,
    status: DocumentStatus = "draft",
    notes: str | None = None,
    total_ht: float | None = None,
    tva_rate: float = 0.0,
    total_ttc: float | None = None,
    pdf_path: str | None = None,
    sent_at: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any]:
    kind = type.strip().lower()
    if kind not in _DOCUMENT_TYPES:
        raise ValueError("type document invalide.")

    stat = status.strip().lower()
    if stat not in _DOCUMENT_STATUSES:
        raise ValueError("status invalide.")

    clean_title = title.strip()
    if not clean_title:
        raise ValueError("title est requis.")

    doc_number = (number or next_document_number(kind)).strip()
    did = (document_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    ht = _round_money(total_ht if total_ht is not None else 0.0)
    rate = max(0.0, float(tva_rate))
    ttc = (
        _round_money(total_ttc)
        if total_ttc is not None
        else _compute_ttc(ht, rate)
    )

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO documents (
                    id, type, number, client_id, project_id, status, title, notes,
                    total_ht, tva_rate, total_ttc, pdf_path, sent_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    did,
                    kind,
                    doc_number,
                    client_id.strip() if client_id else None,
                    project_id.strip() if project_id else None,
                    stat,
                    clean_title,
                    notes.strip() if notes else None,
                    ht,
                    rate,
                    ttc,
                    pdf_path.strip() if pdf_path else None,
                    sent_at,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (did,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Document non retrouvé après insertion.")
            return result
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Numéro ou id document déjà utilisé : {doc_number}") from exc
        finally:
            conn.close()


def get_document(document_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_documents(
    *,
    type: DocumentType | None = None,
    status: DocumentStatus | None = None,
    client_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if type:
        kind = type.strip().lower()
        if kind not in _DOCUMENT_TYPES:
            raise ValueError("type document invalide.")
        clauses.append("type = ?")
        params.append(kind)

    if status:
        stat = status.strip().lower()
        if stat not in _DOCUMENT_STATUSES:
            raise ValueError("status invalide.")
        clauses.append("status = ?")
        params.append(stat)

    if client_id:
        clauses.append("client_id = ?")
        params.append(client_id.strip())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 2000))

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM documents
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, safe_limit),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def update_document(document_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "type",
        "number",
        "client_id",
        "project_id",
        "status",
        "title",
        "notes",
        "total_ht",
        "tva_rate",
        "total_ttc",
        "pdf_path",
        "sent_at",
    }
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "type":
            kind = str(value).strip().lower()
            if kind not in _DOCUMENT_TYPES:
                raise ValueError("type document invalide.")
            updates[key] = kind
        elif key == "status":
            stat = str(value).strip().lower()
            if stat not in _DOCUMENT_STATUSES:
                raise ValueError("status invalide.")
            updates[key] = stat
        elif isinstance(value, str):
            updates[key] = value.strip() if value else value
        else:
            updates[key] = value

    if not updates:
        return get_document(document_id)

    if "total_ht" in updates or "tva_rate" in updates:
        current = get_document(document_id)
        if current:
            ht = _round_money(
                updates.get("total_ht", current.get("total_ht", 0))
            )
            rate = float(updates.get("tva_rate", current.get("tva_rate", 0)))
            updates["total_ht"] = ht
            if "total_ttc" not in updates:
                updates["total_ttc"] = _compute_ttc(ht, rate)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [document_id.strip()]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE documents SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id.strip(),),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def delete_document(document_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id.strip(),),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- Line items ---


def _line_item_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    data = _row_to_dict(row)
    if data is None:
        return None
    if "order" in data:
        data["order"] = int(data["order"])
    return data


def add_line_item(
    *,
    document_id: str,
    description: str,
    quantity: float = 1.0,
    unit_price: float = 0.0,
    order: int | None = None,
    line_item_id: str | None = None,
) -> dict[str, Any]:
    did = document_id.strip()
    desc = description.strip()
    if not desc:
        raise ValueError("description est requise.")

    qty = max(0.0, float(quantity))
    unit = float(unit_price)
    line_total = _round_money(qty * unit)
    lid = (line_item_id or str(uuid.uuid4())).strip()

    with _lock:
        conn = _connect()
        try:
            doc = conn.execute(
                "SELECT 1 FROM documents WHERE id = ?",
                (did,),
            ).fetchone()
            if doc is None:
                raise ValueError(f"Document inconnu : {did}")

            if order is None:
                row = conn.execute(
                    'SELECT COALESCE(MAX("order"), -1) FROM line_items WHERE document_id = ?',
                    (did,),
                ).fetchone()
                line_order = int(row[0]) + 1
            else:
                line_order = int(order)

            conn.execute(
                """
                INSERT INTO line_items (
                    id, document_id, description, quantity, unit_price, total, "order"
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lid, did, desc, qty, unit, line_total, line_order),
            )
            _recalc_document_totals(conn, did)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM line_items WHERE id = ?",
                (lid,),
            ).fetchone()
            result = _line_item_row_to_dict(row)
            if result is None:
                raise RuntimeError("Ligne non retrouvée après insertion.")
            return result
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Ligne déjà existante : {lid}") from exc
        finally:
            conn.close()


def get_line_items(document_id: str) -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM line_items
                WHERE document_id = ?
                ORDER BY "order" ASC
                """,
                (document_id.strip(),),
            ).fetchall()
            items = []
            for row in rows:
                item = _line_item_row_to_dict(row)
                if item:
                    items.append(item)
            return items
        finally:
            conn.close()


def update_line_item(line_item_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"description", "quantity", "unit_price", "total", "order"}
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        updates[key] = value

    if not updates:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT * FROM line_items WHERE id = ?",
                    (line_item_id.strip(),),
                ).fetchone()
                return _line_item_row_to_dict(row)
            finally:
                conn.close()

    if "quantity" in updates or "unit_price" in updates:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT quantity, unit_price FROM line_items WHERE id = ?",
                    (line_item_id.strip(),),
                ).fetchone()
                if row is None:
                    return None
                qty = float(
                    updates.get("quantity", row["quantity"])
                )
                unit = float(
                    updates.get("unit_price", row["unit_price"])
                )
                updates["total"] = _round_money(qty * unit)
            finally:
                conn.close()

    set_parts: list[str] = []
    params: list[Any] = []
    for col, val in updates.items():
        col_sql = '"order"' if col == "order" else col
        set_parts.append(f"{col_sql} = ?")
        params.append(val)

    params.append(line_item_id.strip())

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE line_items SET {', '.join(set_parts)} WHERE id = ?",
                params,
            )
            if cur.rowcount == 0:
                conn.commit()
                return None
            row = conn.execute(
                "SELECT document_id FROM line_items WHERE id = ?",
                (line_item_id.strip(),),
            ).fetchone()
            if row:
                _recalc_document_totals(conn, str(row[0]))
            conn.commit()
            item_row = conn.execute(
                "SELECT * FROM line_items WHERE id = ?",
                (line_item_id.strip(),),
            ).fetchone()
            return _line_item_row_to_dict(item_row)
        finally:
            conn.close()


def delete_line_item(line_item_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT document_id FROM line_items WHERE id = ?",
                (line_item_id.strip(),),
            ).fetchone()
            cur = conn.execute(
                "DELETE FROM line_items WHERE id = ?",
                (line_item_id.strip(),),
            )
            if row:
                _recalc_document_totals(conn, str(row[0]))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
