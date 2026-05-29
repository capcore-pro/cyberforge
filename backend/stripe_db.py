"""
Configuration Stripe par projet — tables dans cockpit.db.
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now
from tools.demo_password_vault import decrypt_demo_password, encrypt_demo_password

StripeMode = Literal["test", "live"]
TransactionType = Literal["one_shot", "subscription"]
TransactionStatus = Literal["pending", "paid", "failed", "refunded"]
SubscriptionStatus = Literal["active", "cancelled", "past_due"]

_MODES = frozenset({"test", "live"})
_TRANSACTION_TYPES = frozenset({"one_shot", "subscription"})
_TRANSACTION_STATUSES = frozenset({"pending", "paid", "failed", "refunded"})
_SUBSCRIPTION_STATUSES = frozenset({"active", "cancelled", "past_due"})

_CONFIG_UPDATABLE = frozenset(
    {
        "project_id",
        "project_name",
        "publishable_key",
        "secret_key_encrypted",
        "webhook_secret_encrypted",
        "mode",
        "currency",
        "enabled",
    }
)
_SUBSCRIPTION_UPDATABLE = frozenset(
    {
        "stripe_config_id",
        "project_id",
        "stripe_subscription_id",
        "customer_email",
        "plan_name",
        "amount_eur",
        "status",
        "current_period_end",
    }
)


def init_stripe_db() -> None:
    """Crée les tables Stripe (même fichier SQLite que le cockpit)."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stripe_configs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL UNIQUE,
                    project_name TEXT NOT NULL,
                    publishable_key TEXT NOT NULL,
                    secret_key_encrypted TEXT NOT NULL,
                    webhook_secret_encrypted TEXT,
                    mode TEXT NOT NULL DEFAULT 'test' CHECK (mode IN ('test', 'live')),
                    currency TEXT NOT NULL DEFAULT 'eur',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stripe_transactions (
                    id TEXT PRIMARY KEY,
                    stripe_config_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stripe_payment_intent_id TEXT NOT NULL,
                    stripe_session_id TEXT,
                    type TEXT NOT NULL CHECK (type IN ('one_shot', 'subscription')),
                    amount_eur REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'paid', 'failed', 'refunded')
                    ),
                    customer_email TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (stripe_config_id) REFERENCES stripe_configs(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                    id TEXT PRIMARY KEY,
                    stripe_config_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    stripe_subscription_id TEXT NOT NULL UNIQUE,
                    customer_email TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    amount_eur REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active' CHECK (
                        status IN ('active', 'cancelled', 'past_due')
                    ),
                    current_period_end TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (stripe_config_id) REFERENCES stripe_configs(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_stripe_configs_enabled
                    ON stripe_configs (enabled, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_stripe_transactions_project
                    ON stripe_transactions (project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_stripe_transactions_status
                    ON stripe_transactions (status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_stripe_transactions_payment_intent
                    ON stripe_transactions (stripe_payment_intent_id);
                CREATE INDEX IF NOT EXISTS idx_stripe_subscriptions_project
                    ON stripe_subscriptions (project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_stripe_subscriptions_status
                    ON stripe_subscriptions (status, created_at DESC);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _config_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    data = _row_to_dict(row)
    if data is None:
        return None
    if "enabled" in data:
        data["enabled"] = bool(data["enabled"])
    return data


def _configs_from_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = _config_from_row(row)
        if item:
            out.append(item)
    return out


def _normalize_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in _MODES:
        raise ValueError("mode invalide (test, live).")
    return mode


def _normalize_transaction_type(value: str) -> str:
    kind = value.strip().lower()
    if kind not in _TRANSACTION_TYPES:
        raise ValueError("type invalide (one_shot, subscription).")
    return kind


def _normalize_transaction_status(value: str) -> str:
    status = value.strip().lower()
    if status not in _TRANSACTION_STATUSES:
        raise ValueError("status invalide (pending, paid, failed, refunded).")
    return status


def _normalize_subscription_status(value: str) -> str:
    status = value.strip().lower()
    if status not in _SUBSCRIPTION_STATUSES:
        raise ValueError("status invalide (active, cancelled, past_due).")
    return status


def decrypt_config_secret(encrypted: str | None) -> str | None:
    """Déchiffre une clé Stripe stockée (secret ou webhook)."""
    return decrypt_demo_password(encrypted)


# --- Configs ---


def add_config(
    *,
    project_id: str,
    project_name: str,
    publishable_key: str,
    secret_key: str,
    mode: StripeMode = "test",
    currency: str = "eur",
    webhook_secret: str | None = None,
    enabled: bool = True,
    config_id: str | None = None,
) -> dict[str, Any]:
    clean_project_id = project_id.strip()
    clean_name = project_name.strip()
    clean_pk = publishable_key.strip()
    clean_sk = secret_key.strip()
    if not clean_project_id:
        raise ValueError("project_id est requis.")
    if not clean_name:
        raise ValueError("project_name est requis.")
    if not clean_pk:
        raise ValueError("publishable_key est requis.")
    if not clean_sk:
        raise ValueError("secret_key est requis.")

    cid = (config_id or str(uuid.uuid4())).strip()
    now = _utc_now()
    secret_enc = encrypt_demo_password(clean_sk)
    webhook_enc = (
        encrypt_demo_password(webhook_secret.strip())
        if webhook_secret and webhook_secret.strip()
        else None
    )

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO stripe_configs (
                    id,
                    project_id,
                    project_name,
                    publishable_key,
                    secret_key_encrypted,
                    webhook_secret_encrypted,
                    mode,
                    currency,
                    enabled,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    clean_project_id,
                    clean_name,
                    clean_pk,
                    secret_enc,
                    webhook_enc,
                    _normalize_mode(mode),
                    currency.strip().lower() or "eur",
                    1 if enabled else 0,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM stripe_configs WHERE id = ?",
                (cid,),
            ).fetchone()
            result = _config_from_row(row)
            if result is None:
                raise RuntimeError("Configuration Stripe introuvable après insertion.")
            return result
        finally:
            conn.close()


def get_config(config_id: str) -> dict[str, Any] | None:
    cid = config_id.strip()
    if not cid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_configs WHERE id = ?",
                (cid,),
            ).fetchone()
            return _config_from_row(row)
        finally:
            conn.close()


def get_config_by_project(project_id: str) -> dict[str, Any] | None:
    pid = project_id.strip()
    if not pid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_configs WHERE project_id = ?",
                (pid,),
            ).fetchone()
            return _config_from_row(row)
        finally:
            conn.close()


def list_configs(*, enabled_only: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    with _lock:
        conn = _connect()
        try:
            if enabled_only:
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_configs
                    WHERE enabled = 1
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (cap,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_configs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (cap,),
                ).fetchall()
            return _configs_from_rows(rows)
        finally:
            conn.close()


def update_config(config_id: str, **fields: Any) -> dict[str, Any] | None:
    cid = config_id.strip()
    if not cid:
        return None

    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _CONFIG_UPDATABLE:
            continue
        if key == "project_id":
            clean = str(value).strip()
            if not clean:
                raise ValueError("project_id ne peut pas être vide.")
            updates[key] = clean
        elif key == "project_name":
            clean = str(value).strip()
            if not clean:
                raise ValueError("project_name ne peut pas être vide.")
            updates[key] = clean
        elif key == "publishable_key":
            clean = str(value).strip()
            if not clean:
                raise ValueError("publishable_key ne peut pas être vide.")
            updates[key] = clean
        elif key == "secret_key_encrypted":
            clean = str(value).strip()
            if not clean:
                raise ValueError("secret_key_encrypted ne peut pas être vide.")
            updates[key] = clean
        elif key == "secret_key":
            clean = str(value).strip()
            if not clean:
                raise ValueError("secret_key ne peut pas être vide.")
            updates["secret_key_encrypted"] = encrypt_demo_password(clean)
        elif key == "webhook_secret_encrypted":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = encrypt_demo_password(clean) if clean else None
        elif key == "webhook_secret":
            if value is None:
                updates["webhook_secret_encrypted"] = None
            else:
                clean = str(value).strip()
                updates["webhook_secret_encrypted"] = (
                    encrypt_demo_password(clean) if clean else None
                )
        elif key == "mode":
            updates[key] = _normalize_mode(str(value))
        elif key == "currency":
            updates[key] = str(value).strip().lower() or "eur"
        elif key == "enabled":
            updates[key] = 1 if bool(value) else 0
        else:
            updates[key] = value

    if not updates:
        return get_config(cid)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [cid]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE stripe_configs SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM stripe_configs WHERE id = ?",
                (cid,),
            ).fetchone()
            return _config_from_row(row)
        finally:
            conn.close()


def delete_config(config_id: str) -> bool:
    cid = config_id.strip()
    if not cid:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM stripe_configs WHERE id = ?", (cid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# --- Transactions ---


def add_transaction(
    *,
    stripe_config_id: str,
    project_id: str,
    stripe_payment_intent_id: str,
    amount_eur: float,
    type: TransactionType,
    status: TransactionStatus = "pending",
    stripe_session_id: str | None = None,
    customer_email: str | None = None,
    description: str | None = None,
    transaction_id: str | None = None,
) -> dict[str, Any]:
    config_id = stripe_config_id.strip()
    pid = project_id.strip()
    pi = stripe_payment_intent_id.strip()
    if not config_id:
        raise ValueError("stripe_config_id est requis.")
    if not pid:
        raise ValueError("project_id est requis.")
    if not pi:
        raise ValueError("stripe_payment_intent_id est requis.")

    tid = (transaction_id or str(uuid.uuid4())).strip()
    now = _utc_now()
    email = (
        customer_email.strip().lower()
        if customer_email and customer_email.strip()
        else None
    )
    session_id = (
        stripe_session_id.strip()
        if stripe_session_id and stripe_session_id.strip()
        else None
    )
    desc = description.strip() if description and description.strip() else None

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO stripe_transactions (
                    id,
                    stripe_config_id,
                    project_id,
                    stripe_payment_intent_id,
                    stripe_session_id,
                    type,
                    amount_eur,
                    status,
                    customer_email,
                    description,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    config_id,
                    pid,
                    pi,
                    session_id,
                    _normalize_transaction_type(type),
                    float(amount_eur),
                    _normalize_transaction_status(status),
                    email,
                    desc,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM stripe_transactions WHERE id = ?",
                (tid,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Transaction introuvable après insertion.")
            return result
        finally:
            conn.close()


def get_transaction_by_session(stripe_session_id: str) -> dict[str, Any] | None:
    session_id = stripe_session_id.strip()
    if not session_id:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_transactions WHERE stripe_session_id = ?",
                (session_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def get_transaction_by_payment_intent(
    stripe_payment_intent_id: str,
) -> dict[str, Any] | None:
    pi_id = stripe_payment_intent_id.strip()
    if not pi_id:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_transactions WHERE stripe_payment_intent_id = ?",
                (pi_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


_TRANSACTION_UPDATABLE = frozenset(
    {
        "status",
        "customer_email",
        "description",
        "amount_eur",
        "stripe_session_id",
    }
)


def update_transaction(transaction_id: str, **fields: Any) -> dict[str, Any] | None:
    tid = transaction_id.strip()
    if not tid:
        return None

    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _TRANSACTION_UPDATABLE:
            continue
        if key == "status":
            updates[key] = _normalize_transaction_status(str(value))
        elif key == "customer_email":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip().lower()
                updates[key] = clean or None
        elif key == "description":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = clean or None
        elif key == "amount_eur":
            updates[key] = float(value)
        elif key == "stripe_session_id":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = clean or None
        else:
            updates[key] = value

    if not updates:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT * FROM stripe_transactions WHERE id = ?",
                    (tid,),
                ).fetchone()
                return _row_to_dict(row)
            finally:
                conn.close()

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [tid]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE stripe_transactions SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM stripe_transactions WHERE id = ?",
                (tid,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_transactions(
    project_id: str | None = None,
    status: TransactionStatus | str | None = None,
    type: TransactionType | str | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    pid = project_id.strip() if project_id else None
    tx_type = _normalize_transaction_type(str(type)) if type is not None else None
    stat = _normalize_transaction_status(str(status)) if status is not None else None

    clauses: list[str] = []
    params: list[Any] = []
    if pid:
        clauses.append("project_id = ?")
        params.append(pid)
    if stat is not None:
        clauses.append("status = ?")
        params.append(stat)
    if tx_type is not None:
        clauses.append("type = ?")
        params.append(tx_type)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(cap)

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM stripe_transactions
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()


# --- Subscriptions ---


def add_subscription(
    *,
    stripe_config_id: str,
    project_id: str,
    stripe_subscription_id: str,
    customer_email: str,
    plan_name: str,
    amount_eur: float,
    status: SubscriptionStatus = "active",
    current_period_end: str | None = None,
    subscription_id: str | None = None,
) -> dict[str, Any]:
    config_id = stripe_config_id.strip()
    pid = project_id.strip()
    sub_stripe_id = stripe_subscription_id.strip()
    email = customer_email.strip().lower()
    plan = plan_name.strip()
    if not config_id:
        raise ValueError("stripe_config_id est requis.")
    if not pid:
        raise ValueError("project_id est requis.")
    if not sub_stripe_id:
        raise ValueError("stripe_subscription_id est requis.")
    if not email:
        raise ValueError("customer_email est requis.")
    if not plan:
        raise ValueError("plan_name est requis.")

    sid = (subscription_id or str(uuid.uuid4())).strip()
    now = _utc_now()
    period_end = (
        current_period_end.strip()
        if current_period_end and current_period_end.strip()
        else None
    )

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO stripe_subscriptions (
                    id,
                    stripe_config_id,
                    project_id,
                    stripe_subscription_id,
                    customer_email,
                    plan_name,
                    amount_eur,
                    status,
                    current_period_end,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    config_id,
                    pid,
                    sub_stripe_id,
                    email,
                    plan,
                    float(amount_eur),
                    _normalize_subscription_status(status),
                    period_end,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM stripe_subscriptions WHERE id = ?",
                (sid,),
            ).fetchone()
            result = _row_to_dict(row)
            if result is None:
                raise RuntimeError("Abonnement introuvable après insertion.")
            return result
        finally:
            conn.close()


def get_subscription(stripe_subscription_id: str) -> dict[str, Any] | None:
    sub_id = stripe_subscription_id.strip()
    if not sub_id:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_subscriptions WHERE stripe_subscription_id = ?",
                (sub_id,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def get_subscription_by_id(subscription_id: str) -> dict[str, Any] | None:
    sid = subscription_id.strip()
    if not sid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM stripe_subscriptions WHERE id = ?",
                (sid,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def update_subscription(subscription_id: str, **fields: Any) -> dict[str, Any] | None:
    sid = subscription_id.strip()
    if not sid:
        return None

    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _SUBSCRIPTION_UPDATABLE:
            continue
        if key in ("stripe_config_id", "project_id", "stripe_subscription_id"):
            clean = str(value).strip()
            if not clean:
                raise ValueError(f"{key} ne peut pas être vide.")
            updates[key] = clean
        elif key == "customer_email":
            clean = str(value).strip().lower()
            if not clean:
                raise ValueError("customer_email ne peut pas être vide.")
            updates[key] = clean
        elif key == "plan_name":
            clean = str(value).strip()
            if not clean:
                raise ValueError("plan_name ne peut pas être vide.")
            updates[key] = clean
        elif key == "amount_eur":
            updates[key] = float(value)
        elif key == "status":
            updates[key] = _normalize_subscription_status(str(value))
        elif key == "current_period_end":
            if value is None:
                updates[key] = None
            else:
                clean = str(value).strip()
                updates[key] = clean or None
        else:
            updates[key] = value

    if not updates:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT * FROM stripe_subscriptions WHERE id = ?",
                    (sid,),
                ).fetchone()
                return _row_to_dict(row)
            finally:
                conn.close()

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [sid]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE stripe_subscriptions SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM stripe_subscriptions WHERE id = ?",
                (sid,),
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_subscriptions(
    project_id: str | None = None,
    status: SubscriptionStatus | str | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    pid = project_id.strip() if project_id else None
    with _lock:
        conn = _connect()
        try:
            if pid and status is not None:
                stat = _normalize_subscription_status(str(status))
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_subscriptions
                    WHERE project_id = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (pid, stat, cap),
                ).fetchall()
            elif pid:
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_subscriptions
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (pid, cap),
                ).fetchall()
            elif status is not None:
                stat = _normalize_subscription_status(str(status))
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_subscriptions
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (stat, cap),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM stripe_subscriptions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (cap,),
                ).fetchall()
            return _rows_to_dicts(rows)
        finally:
            conn.close()
