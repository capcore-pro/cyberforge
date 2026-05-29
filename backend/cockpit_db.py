"""
Base SQLite locale — cockpit financier (services API, soldes, alertes).

Fichier : backend/cockpit.db
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).resolve().parent / "cockpit.db"
_lock = threading.RLock()

_DEFAULT_WARNING_EUR = 15.0
_DEFAULT_CRITICAL_EUR = 5.0
_DEFAULT_URGENT_EUR = 2.0

_SEED_SERVICES: tuple[dict[str, Any], ...] = (
    {
        "id": "anthropic",
        "name": "Anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "connector": "anthropic",
        "color": "#7C3AED",
        "icon": "🤖",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "connector": "deepseek",
        "color": "#0EA5E9",
        "icon": "🧠",
    },
    {
        "id": "v0",
        "name": "v0",
        "api_key_env": "V0_API_KEY",
        "connector": "v0",
        "color": "#000000",
        "icon": "▲",
    },
    {
        "id": "replicate",
        "name": "Replicate",
        "api_key_env": "REPLICATE_API_KEY",
        "connector": "replicate",
        "color": "#6366F1",
        "icon": "🖼️",
    },
    {
        "id": "tavily",
        "name": "Tavily",
        "api_key_env": "TAVILY_API_KEY",
        "connector": "tavily",
        "color": "#14B8A6",
        "icon": "🔍",
    },
    {
        "id": "railway",
        "name": "Railway",
        "api_key_env": "RAILWAY_API_KEY",
        "connector": "railway",
        "color": "#9333EA",
        "icon": "🚂",
    },
    {
        "id": "vercel",
        "name": "Vercel",
        "api_key_env": "VERCEL_TOKEN",
        "connector": "vercel",
        "color": "#E5E5E5",
        "icon": "▲",
    },
    {
        "id": "cloudflare",
        "name": "Cloudflare",
        "api_key_env": "CLOUDFLARE_API_TOKEN",
        "connector": "cloudflare",
        "color": "#F97316",
        "icon": "☁️",
    },
    {
        "id": "brevo",
        "name": "Brevo",
        "api_key_env": "BREVO_API_KEY",
        "connector": "brevo",
        "color": "#2563EB",
        "icon": "✉️",
    },
    {
        "id": "github",
        "name": "GitHub",
        "api_key_env": "GITHUB_TOKEN",
        "connector": "github",
        "color": "#6B7280",
        "icon": "🐙",
    },
    {
        "id": "unsplash",
        "name": "Unsplash",
        "api_key_env": "UNSPLASH_ACCESS_KEY",
        "connector": "unsplash",
        "color": "#111827",
        "icon": "📷",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in rows]  # type: ignore[misc]


def _slugify_id(name: str) -> str:
    base = "".join(ch if ch.isalnum() else "-" for ch in name.strip().lower())
    parts = [p for p in base.split("-") if p]
    return "-".join(parts) or str(uuid.uuid4())


def init_db() -> None:
    """Crée les tables et pré-insère les services par défaut si la base est vide."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    api_key_env TEXT NOT NULL,
                    connector TEXT,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    color TEXT,
                    icon TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS balances (
                    service_id TEXT PRIMARY KEY,
                    balance_eur REAL NOT NULL DEFAULT 0,
                    last_synced_at TEXT,
                    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    service_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('expense', 'topup')),
                    amount_eur REAL NOT NULL,
                    description TEXT,
                    project_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS thresholds (
                    service_id TEXT PRIMARY KEY,
                    warning_eur REAL NOT NULL DEFAULT 15,
                    critical_eur REAL NOT NULL DEFAULT 5,
                    urgent_eur REAL NOT NULL DEFAULT 2,
                    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    service_id TEXT NOT NULL,
                    level TEXT NOT NULL CHECK (level IN ('warning', 'critical', 'urgent')),
                    message TEXT NOT NULL,
                    read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_transactions_service_created
                    ON transactions (service_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_alerts_unread
                    ON alerts (read, created_at DESC);
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
            if count == 0:
                now = _utc_now()
                for seed in _SEED_SERVICES:
                    conn.execute(
                        """
                        INSERT INTO services (
                            id, name, api_key_env, connector, currency, color, icon, enabled, created_at
                        ) VALUES (?, ?, ?, ?, 'EUR', ?, ?, 1, ?)
                        """,
                        (
                            seed["id"],
                            seed["name"],
                            seed["api_key_env"],
                            seed.get("connector"),
                            seed.get("color"),
                            seed.get("icon"),
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO balances (service_id, balance_eur, last_synced_at)
                        VALUES (?, 0, NULL)
                        """,
                        (seed["id"],),
                    )
                    conn.execute(
                        """
                        INSERT INTO thresholds (service_id, warning_eur, critical_eur, urgent_eur)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            seed["id"],
                            _DEFAULT_WARNING_EUR,
                            _DEFAULT_CRITICAL_EUR,
                            _DEFAULT_URGENT_EUR,
                        ),
                    )
            conn.commit()
        finally:
            conn.close()

    from desktop_app_db import init_desktop_db
    from legal_db import init_legal_db
    from media_db import init_media_db
    from newsletter_db import init_newsletter_db
    from stripe_db import init_stripe_db

    init_media_db()
    init_legal_db()
    init_newsletter_db()
    init_desktop_db()
    init_stripe_db()


def get_all_services(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        try:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM services WHERE enabled = 1 ORDER BY name COLLATE NOCASE"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM services ORDER BY name COLLATE NOCASE"
                ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def add_service(
    *,
    name: str,
    api_key_env: str,
    connector: str | None = None,
    currency: str = "EUR",
    color: str | None = None,
    icon: str | None = None,
    enabled: bool = True,
    service_id: str | None = None,
) -> str:
    """Ajoute un fournisseur ; retourne son id."""
    clean_name = name.strip()
    clean_env = api_key_env.strip()
    if not clean_name or not clean_env:
        raise ValueError("name et api_key_env sont requis.")

    sid = (service_id or _slugify_id(clean_name)).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO services (
                    id, name, api_key_env, connector, currency, color, icon, enabled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    clean_name,
                    clean_env,
                    connector.strip() if connector else None,
                    currency.strip() or "EUR",
                    color,
                    icon,
                    1 if enabled else 0,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO balances (service_id, balance_eur, last_synced_at) VALUES (?, 0, NULL)",
                (sid,),
            )
            conn.execute(
                """
                INSERT INTO thresholds (service_id, warning_eur, critical_eur, urgent_eur)
                VALUES (?, ?, ?, ?)
                """,
                (sid, _DEFAULT_WARNING_EUR, _DEFAULT_CRITICAL_EUR, _DEFAULT_URGENT_EUR),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Service déjà existant : {sid}") from exc
        finally:
            conn.close()
    return sid


def update_service(service_id: str, **fields: Any) -> dict[str, Any] | None:
    """Met à jour un service (champs fournis uniquement)."""
    allowed = {
        "name",
        "api_key_env",
        "connector",
        "currency",
        "color",
        "icon",
        "enabled",
    }
    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "enabled":
            updates[key] = 1 if value else 0
        elif isinstance(value, str):
            updates[key] = value.strip() if value else value
        else:
            updates[key] = value

    if not updates:
        return get_service(service_id)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [service_id]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE services SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
        finally:
            conn.close()
    return get_service(service_id)


def get_service(service_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM services WHERE id = ?",
                (service_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def delete_service(service_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_balance(service_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM balances WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def set_balance(service_id: str, amount: float) -> dict[str, Any]:
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO balances (service_id, balance_eur, last_synced_at)
                VALUES (?, ?, ?)
                ON CONFLICT(service_id) DO UPDATE SET
                    balance_eur = excluded.balance_eur,
                    last_synced_at = excluded.last_synced_at
                """,
                (service_id, float(amount), now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM balances WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise ValueError(f"Service inconnu : {service_id}")
            return result
        finally:
            conn.close()


def add_transaction(
    *,
    service_id: str,
    type: str,
    amount_eur: float,
    description: str | None = None,
    project_id: str | None = None,
    transaction_id: str | None = None,
) -> dict[str, Any]:
    tx_type = type.strip().lower()
    if tx_type not in ("expense", "topup"):
        raise ValueError("type doit être 'expense' ou 'topup'.")

    tx_id = transaction_id or str(uuid.uuid4())
    now = _utc_now()
    amount = float(amount_eur)

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO transactions (
                    id, service_id, type, amount_eur, description, project_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id,
                    service_id,
                    tx_type,
                    amount,
                    description,
                    project_id,
                    now,
                ),
            )
            delta = -amount if tx_type == "expense" else amount
            exists = conn.execute(
                "SELECT 1 FROM balances WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE balances
                    SET balance_eur = balance_eur + ?, last_synced_at = ?
                    WHERE service_id = ?
                    """,
                    (delta, now, service_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO balances (service_id, balance_eur, last_synced_at)
                    VALUES (?, ?, ?)
                    """,
                    (service_id, delta, now),
                )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (tx_id,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Transaction non retrouvée après insertion.")
            return result
        finally:
            conn.close()


def get_transactions(
    service_id: str,
    limit: int = 50,
    *,
    tx_type: str | None = None,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    type_filter = (tx_type or "").strip().lower()
    if type_filter and type_filter not in ("expense", "topup"):
        raise ValueError("type doit être 'expense' ou 'topup'.")

    with _lock:
        conn = _connect()
        try:
            if type_filter:
                rows = conn.execute(
                    """
                    SELECT * FROM transactions
                    WHERE service_id = ? AND type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (service_id, type_filter, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM transactions
                    WHERE service_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (service_id, safe_limit),
                ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def get_all_balances() -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT b.*, s.name AS service_name
                FROM balances b
                JOIN services s ON s.id = b.service_id
                ORDER BY s.name COLLATE NOCASE
                """
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def sum_expenses_since(iso_from: str) -> float:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(amount_eur), 0)
                FROM transactions
                WHERE type = 'expense' AND created_at >= ?
                """,
                (iso_from,),
            ).fetchone()
            return float(row[0] if row else 0)
        finally:
            conn.close()


def get_expense_aggregates() -> dict[str, float]:
    """Dépenses (type expense) aujourd'hui, cette semaine et ce mois (UTC)."""
    now = datetime.now(timezone.utc)
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_day - timedelta(days=start_day.weekday())
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_total = sum_expenses_since(start_month.isoformat())
    return {
        "today_eur": round(sum_expenses_since(start_day.isoformat()), 8),
        "week_eur": round(sum_expenses_since(start_week.isoformat()), 8),
        "month_eur": round(month_total, 8),
        "month_total_eur": round(month_total, 8),
    }


def has_unread_alert(service_id: str, level: str) -> bool:
    lvl = level.strip().lower()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT 1 FROM alerts
                WHERE service_id = ? AND level = ? AND read = 0
                LIMIT 1
                """,
                (service_id, lvl),
            ).fetchone()
            return row is not None
        finally:
            conn.close()


def get_thresholds(service_id: str) -> dict[str, Any]:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM thresholds WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            if row is not None:
                return _row_to_dict(row)  # type: ignore[return-value]
            return {
                "service_id": service_id,
                "warning_eur": _DEFAULT_WARNING_EUR,
                "critical_eur": _DEFAULT_CRITICAL_EUR,
                "urgent_eur": _DEFAULT_URGENT_EUR,
            }
        finally:
            conn.close()


def set_thresholds(
    service_id: str,
    *,
    warning_eur: float | None = None,
    critical_eur: float | None = None,
    urgent_eur: float | None = None,
) -> dict[str, Any]:
    current = get_thresholds(service_id)
    warning = float(warning_eur if warning_eur is not None else current["warning_eur"])
    critical = float(critical_eur if critical_eur is not None else current["critical_eur"])
    urgent = float(urgent_eur if urgent_eur is not None else current["urgent_eur"])

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO thresholds (service_id, warning_eur, critical_eur, urgent_eur)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(service_id) DO UPDATE SET
                    warning_eur = excluded.warning_eur,
                    critical_eur = excluded.critical_eur,
                    urgent_eur = excluded.urgent_eur
                """,
                (service_id, warning, critical, urgent),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM thresholds WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            return _row_to_dict(row)  # type: ignore[return-value]
        finally:
            conn.close()


def add_alert(
    *,
    service_id: str,
    level: str,
    message: str,
    alert_id: str | None = None,
) -> dict[str, Any]:
    lvl = level.strip().lower()
    if lvl not in ("warning", "critical", "urgent"):
        raise ValueError("level doit être warning, critical ou urgent.")

    aid = alert_id or str(uuid.uuid4())
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO alerts (id, service_id, level, message, read, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (aid, service_id, lvl, message.strip(), now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM alerts WHERE id = ?",
                (aid,),
            ).fetchone()
            return _row_to_dict(row)  # type: ignore[return-value]
        finally:
            conn.close()


def get_unread_alerts(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM alerts
                WHERE read = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


def mark_alerts_read(alert_ids: list[str] | None = None) -> int:
    """Marque des alertes comme lues. Sans ids, marque toutes les non lues."""
    with _lock:
        conn = _connect()
        try:
            if alert_ids:
                placeholders = ",".join("?" for _ in alert_ids)
                cur = conn.execute(
                    f"UPDATE alerts SET read = 1 WHERE id IN ({placeholders})",
                    alert_ids,
                )
            else:
                cur = conn.execute("UPDATE alerts SET read = 1 WHERE read = 0")
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()
