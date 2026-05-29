"""
Commandes mini-apps desktop — table desktop_orders dans cockpit.db.
"""

from __future__ import annotations

import secrets
import sqlite3
import uuid
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now

StripePaymentStatus = Literal["pending", "paid", "failed"]
GenerationStatus = Literal["waiting", "generating", "ready", "failed"]

_STRIPE_PAYMENT_STATUSES = frozenset({"pending", "paid", "failed"})
_GENERATION_STATUSES = frozenset({"waiting", "generating", "ready", "failed"})

_UPDATABLE_FIELDS = frozenset(
    {
        "app_type",
        "client_email",
        "client_name",
        "stripe_session_id",
        "stripe_payment_status",
        "generation_status",
        "exe_path",
        "r2_url",
        "download_token",
        "expires_at",
    }
)


def init_desktop_db() -> None:
    """Crée la table desktop_orders et les index (même fichier SQLite que le cockpit)."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS desktop_orders (
                    id TEXT PRIMARY KEY,
                    app_type TEXT NOT NULL,
                    client_email TEXT NOT NULL,
                    client_name TEXT,
                    stripe_session_id TEXT NOT NULL,
                    stripe_payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        stripe_payment_status IN ('pending', 'paid', 'failed')
                    ),
                    generation_status TEXT NOT NULL DEFAULT 'waiting' CHECK (
                        generation_status IN ('waiting', 'generating', 'ready', 'failed')
                    ),
                    exe_path TEXT,
                    r2_url TEXT,
                    download_token TEXT NOT NULL,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_desktop_orders_session
                    ON desktop_orders (stripe_session_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_desktop_orders_token
                    ON desktop_orders (download_token);
                CREATE INDEX IF NOT EXISTS idx_desktop_orders_generation_status
                    ON desktop_orders (generation_status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_desktop_orders_client_email
                    ON desktop_orders (client_email, created_at DESC);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _normalize_stripe_payment_status(value: str) -> str:
    status = value.strip().lower()
    if status not in _STRIPE_PAYMENT_STATUSES:
        raise ValueError(
            "stripe_payment_status invalide (pending, paid, failed)."
        )
    return status


def _normalize_generation_status(value: str) -> str:
    status = value.strip().lower()
    if status not in _GENERATION_STATUSES:
        raise ValueError(
            "generation_status invalide (waiting, generating, ready, failed)."
        )
    return status


def create_order(
    *,
    app_type: str,
    client_email: str,
    stripe_session_id: str,
    client_name: str | None = None,
    stripe_payment_status: StripePaymentStatus = "pending",
    generation_status: GenerationStatus = "waiting",
    order_id: str | None = None,
    download_token: str | None = None,
) -> dict[str, Any]:
    """Crée une commande desktop ; retourne l'enregistrement complet."""
    clean_app = app_type.strip()
    clean_email = client_email.strip().lower()
    clean_session = stripe_session_id.strip()
    if not clean_app:
        raise ValueError("app_type est requis.")
    if not clean_email:
        raise ValueError("client_email est requis.")
    if not clean_session:
        raise ValueError("stripe_session_id est requis.")

    oid = (order_id or str(uuid.uuid4())).strip()
    token = (download_token or secrets.token_urlsafe(32)).strip()
    if not token:
        raise ValueError("download_token est requis.")

    payment_status = _normalize_stripe_payment_status(stripe_payment_status)
    gen_status = _normalize_generation_status(generation_status)
    now = _utc_now()
    clean_name = client_name.strip() if client_name and client_name.strip() else None

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO desktop_orders (
                    id,
                    app_type,
                    client_email,
                    client_name,
                    stripe_session_id,
                    stripe_payment_status,
                    generation_status,
                    exe_path,
                    r2_url,
                    download_token,
                    expires_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, NULL, ?)
                """,
                (
                    oid,
                    clean_app,
                    clean_email,
                    clean_name,
                    clean_session,
                    payment_status,
                    gen_status,
                    token,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM desktop_orders WHERE id = ?",
                (oid,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Commande desktop introuvable après insertion.")
            return result
        finally:
            conn.close()


def get_order(order_id: str) -> dict[str, Any] | None:
    oid = order_id.strip()
    if not oid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM desktop_orders WHERE id = ?",
                (oid,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def get_order_by_session(stripe_session_id: str) -> dict[str, Any] | None:
    session_id = stripe_session_id.strip()
    if not session_id:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM desktop_orders WHERE stripe_session_id = ?",
                (session_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def get_order_by_token(download_token: str) -> dict[str, Any] | None:
    token = download_token.strip()
    if not token:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM desktop_orders WHERE download_token = ?",
                (token,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def update_order(order_id: str, **fields: Any) -> dict[str, Any] | None:
    """Met à jour les champs autorisés d'une commande."""
    oid = order_id.strip()
    if not oid:
        return None

    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _UPDATABLE_FIELDS:
            continue
        if key == "app_type":
            clean = str(value).strip()
            if not clean:
                raise ValueError("app_type ne peut pas être vide.")
            updates[key] = clean
        elif key == "client_email":
            clean = str(value).strip().lower()
            if not clean:
                raise ValueError("client_email ne peut pas être vide.")
            updates[key] = clean
        elif key == "client_name":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = clean or None
        elif key == "stripe_session_id":
            clean = str(value).strip()
            if not clean:
                raise ValueError("stripe_session_id ne peut pas être vide.")
            updates[key] = clean
        elif key == "stripe_payment_status":
            updates[key] = _normalize_stripe_payment_status(str(value))
        elif key == "generation_status":
            updates[key] = _normalize_generation_status(str(value))
        elif key in ("exe_path", "r2_url", "expires_at"):
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = clean or None
        elif key == "download_token":
            clean = str(value).strip()
            if not clean:
                raise ValueError("download_token ne peut pas être vide.")
            updates[key] = clean
        else:
            updates[key] = value

    if not updates:
        return get_order(oid)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [oid]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE desktop_orders SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM desktop_orders WHERE id = ?",
                (oid,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_orders(
    status: GenerationStatus | str | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Liste les commandes, optionnellement filtrées par generation_status."""
    cap = max(1, min(int(limit), 500))
    with _lock:
        conn = _connect()
        try:
            if status is None:
                rows = conn.execute(
                    """
                    SELECT * FROM desktop_orders
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (cap,),
                ).fetchall()
            else:
                gen_status = _normalize_generation_status(str(status))
                rows = conn.execute(
                    """
                    SELECT * FROM desktop_orders
                    WHERE generation_status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (gen_status, cap),
                ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()
