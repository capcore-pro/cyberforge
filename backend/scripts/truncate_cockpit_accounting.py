"""Vide les données comptables dans cockpit.db (SQLite local)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from cockpit_db import _DB_PATH, _connect, _lock  # noqa: E402


def _count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    q = f'SELECT COUNT(*) FROM "{table}"' if table == "line_items" else f"SELECT COUNT(*) FROM {table}"
    if where:
        q += f" WHERE {where}"
    return int(conn.execute(q).fetchone()[0])


def _delete(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    q = f'DELETE FROM "{table}"' if table == "line_items" else f"DELETE FROM {table}"
    if where:
        q += f" WHERE {where}"
    cur = conn.execute(q)
    return cur.rowcount


def main() -> None:
    if not _DB_PATH.exists():
        print(f"Base absente : {_DB_PATH}")
        sys.exit(1)

    print(f"Nettoyage comptable : {_DB_PATH}\n")

    report: dict[str, int | str] = {}

    with _lock:
        conn = _connect()
        try:
            conn.execute("PRAGMA foreign_keys = ON")

            # --- legal_db : devis / factures dans `documents` + lignes ---
            devis_before = _count(conn, "documents", "type = 'devis'")
            factures_before = _count(conn, "documents", "type = 'facture'")
            line_items_before = _count(
                conn,
                "line_items",
                "document_id IN (SELECT id FROM documents WHERE type IN ('devis', 'facture'))",
            )

            deleted_lines = _delete(
                conn,
                "line_items",
                "document_id IN (SELECT id FROM documents WHERE type IN ('devis', 'facture'))",
            )
            deleted_devis = _delete(conn, "documents", "type = 'devis'")
            deleted_factures = _delete(conn, "documents", "type = 'facture'")

            report["line_items (devis/facture)"] = deleted_lines
            report["devis (documents)"] = deleted_devis
            report["factures (documents)"] = deleted_factures

            # --- cockpit_db : transactions API ---
            tx_before = _count(conn, "transactions")
            deleted_tx = _delete(conn, "transactions")
            report["transactions"] = deleted_tx

            # --- stripe_db : paiements (données comptables projet) ---
            stripe_tx_before = _count(conn, "stripe_transactions")
            stripe_sub_before = _count(conn, "stripe_subscriptions")
            deleted_stripe_tx = _delete(conn, "stripe_transactions")
            deleted_stripe_sub = _delete(conn, "stripe_subscriptions")
            report["stripe_transactions"] = deleted_stripe_tx
            report["stripe_subscriptions"] = deleted_stripe_sub

            conn.commit()

            print("=== Lignes supprimées ===")
            print(f"  devis (table documents, type=devis)     : {deleted_devis} (avant: {devis_before})")
            print(f"  factures (table documents, type=facture): {deleted_factures} (avant: {factures_before})")
            print(f"  line_items (liées devis/facture)        : {deleted_lines} (avant: {line_items_before})")
            print(f"  transactions (cockpit API)                : {deleted_tx} (avant: {tx_before})")
            print(f"  stripe_transactions                       : {deleted_stripe_tx} (avant: {stripe_tx_before})")
            print(f"  stripe_subscriptions                      : {deleted_stripe_sub} (avant: {stripe_sub_before})")

            devis_after = _count(conn, "documents", "type = 'devis'")
            facture_after = _count(conn, "documents", "type = 'facture'")
            tx_after = _count(conn, "transactions")
            stripe_tx_after = _count(conn, "stripe_transactions")
            stripe_sub_after = _count(conn, "stripe_subscriptions")

            print("\n=== Vérification (reste) ===")
            print(f"  documents[devis]    : {devis_after}")
            print(f"  documents[facture]  : {facture_after}")
            print(f"  transactions        : {tx_after}")
            print(f"  stripe_transactions : {stripe_tx_after}")
            print(f"  stripe_subscriptions: {stripe_sub_after}")

        finally:
            conn.close()


if __name__ == "__main__":
    main()
