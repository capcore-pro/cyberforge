"""
Projets personnels Mat — métadonnées commerciales (cockpit.db).
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now

PersonalUsage = Literal["personal", "one_shot", "subscription"]
_USAGES = frozenset({"personal", "one_shot", "subscription"})

_UPDATABLE = frozenset(
    {
        "title",
        "usage_type",
        "price_eur",
        "commercial_description",
        "project_key",
        "supabase_project_id",
        "managed_id",
        "demo_id",
        "app_type",
        "sale_link",
        "sales_count",
        "revenue_eur",
        "published_on_capcore",
    }
)


def init_personal_projects_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS personal_projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    usage_type TEXT NOT NULL DEFAULT 'personal' CHECK (
                        usage_type IN ('personal', 'one_shot', 'subscription')
                    ),
                    price_eur REAL,
                    commercial_description TEXT,
                    project_key TEXT,
                    supabase_project_id TEXT,
                    managed_id TEXT,
                    demo_id TEXT,
                    app_type TEXT,
                    sale_link TEXT,
                    sales_count INTEGER NOT NULL DEFAULT 0,
                    revenue_eur REAL NOT NULL DEFAULT 0,
                    published_on_capcore INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_personal_projects_created
                    ON personal_projects (created_at DESC);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    data = _row_to_dict(row)
    if data is None:
        return None
    data["published_on_capcore"] = bool(data.get("published_on_capcore"))
    data["sales_count"] = int(data.get("sales_count") or 0)
    data["revenue_eur"] = float(data.get("revenue_eur") or 0)
    if data.get("price_eur") is not None:
        data["price_eur"] = float(data["price_eur"])
    return data


def list_personal_projects(*, limit: int = 200) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM personal_projects
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cap,),
            ).fetchall()
            return [r for row in rows if (r := _from_row(row)) is not None]
        finally:
            conn.close()


def get_personal_project(project_id: str) -> dict[str, Any] | None:
    pid = project_id.strip()
    if not pid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM personal_projects WHERE id = ?",
                (pid,),
            ).fetchone()
            return _from_row(row)
        finally:
            conn.close()


def create_personal_project(
    *,
    title: str,
    usage_type: PersonalUsage = "personal",
    price_eur: float | None = None,
    commercial_description: str | None = None,
    project_key: str | None = None,
    supabase_project_id: str | None = None,
    managed_id: str | None = None,
    demo_id: str | None = None,
    app_type: str | None = None,
    sale_link: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("title est requis.")
    usage = usage_type.strip().lower()
    if usage not in _USAGES:
        raise ValueError("usage_type invalide.")

    pid = (project_id or str(uuid.uuid4())).strip()
    now = _utc_now()

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO personal_projects (
                    id, title, usage_type, price_eur, commercial_description,
                    project_key, supabase_project_id, managed_id, demo_id,
                    app_type, sale_link, sales_count, revenue_eur,
                    published_on_capcore, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
                """,
                (
                    pid,
                    clean_title,
                    usage,
                    price_eur,
                    (commercial_description or "").strip() or None,
                    (project_key or "").strip() or None,
                    (supabase_project_id or "").strip() or None,
                    (managed_id or "").strip() or None,
                    (demo_id or "").strip() or None,
                    (app_type or "").strip() or None,
                    (sale_link or "").strip() or None,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM personal_projects WHERE id = ?",
                (pid,),
            ).fetchone()
            result = _from_row(row)
            if result is None:
                raise RuntimeError("insertion personal_projects échouée.")
            return result
        finally:
            conn.close()


def update_personal_project(project_id: str, **fields: Any) -> dict[str, Any] | None:
    pid = project_id.strip()
    if not pid:
        return None

    updates: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _UPDATABLE:
            continue
        if key == "title":
            clean = str(value).strip()
            if not clean:
                raise ValueError("title ne peut pas être vide.")
            updates[key] = clean
        elif key == "usage_type":
            usage = str(value).strip().lower()
            if usage not in _USAGES:
                raise ValueError("usage_type invalide.")
            updates[key] = usage
        elif key == "published_on_capcore":
            updates[key] = 1 if bool(value) else 0
        elif key in ("sales_count",):
            updates[key] = max(0, int(value))
        elif key in ("revenue_eur", "price_eur"):
            updates[key] = float(value) if value is not None else None
        else:
            updates[key] = value

    if not updates:
        return get_personal_project(pid)

    updates["updated_at"] = _utc_now()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [pid]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE personal_projects SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM personal_projects WHERE id = ?",
                (pid,),
            ).fetchone()
            return _from_row(row)
        finally:
            conn.close()


def delete_personal_project(project_id: str) -> bool:
    pid = project_id.strip()
    if not pid:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM personal_projects WHERE id = ?",
                (pid,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
