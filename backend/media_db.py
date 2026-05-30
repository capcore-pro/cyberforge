"""
Médiathèque — métadonnées des assets dans cockpit.db (table media_assets).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Literal

from cockpit_db import _connect, _lock, _row_to_dict, _rows_to_dicts, _utc_now

MediaType = Literal["image", "zip", "pdf"]
MediaSource = Literal["upload", "generated"]

_ALLOWED_TYPES = frozenset({"image", "zip", "pdf"})
_ALLOWED_SOURCES = frozenset({"upload", "generated"})


def _normalize_tags(tags: list[str] | str | None) -> str:
    if tags is None:
        return "[]"
    if isinstance(tags, str):
        raw = tags.strip()
        if not raw:
            return "[]"
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return json.dumps([str(t) for t in parsed], ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps([raw], ensure_ascii=False)
        return "[]"
    return json.dumps([str(t).strip() for t in tags if str(t).strip()], ensure_ascii=False)


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(t) for t in parsed]
    except json.JSONDecodeError:
        pass
    return []


def _asset_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    data = _row_to_dict(row)
    if data is None:
        return None
    data["tags"] = _parse_tags(data.get("tags"))
    return data


def init_media_db() -> None:
    """Crée la table media_assets et les index (même fichier SQLite que le cockpit)."""
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS media_assets (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('image', 'zip', 'pdf')),
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    local_path TEXT NOT NULL,
                    r2_url TEXT,
                    r2_key TEXT,
                    project_id TEXT,
                    source TEXT NOT NULL CHECK (source IN ('upload', 'generated')),
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_media_assets_type_created
                    ON media_assets (type, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_media_assets_project_created
                    ON media_assets (project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_media_assets_source_created
                    ON media_assets (source, created_at DESC);

                CREATE TABLE IF NOT EXISTS project_cover_images (
                    project_key TEXT PRIMARY KEY,
                    media_asset_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def add_asset(
    *,
    filename: str,
    type: MediaType,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source: MediaSource,
    tags: list[str] | str | None = None,
    project_id: str | None = None,
    r2_url: str | None = None,
    r2_key: str | None = None,
    asset_id: str | None = None,
) -> dict[str, Any]:
    """Enregistre un asset ; retourne l'enregistrement complet."""
    clean_name = filename.strip()
    clean_path = local_path.strip()
    clean_mime = mime_type.strip()
    media_type = type.strip().lower()
    media_source = source.strip().lower()

    if not clean_name:
        raise ValueError("filename est requis.")
    if not clean_path:
        raise ValueError("local_path est requis.")
    if not clean_mime:
        raise ValueError("mime_type est requis.")
    if media_type not in _ALLOWED_TYPES:
        raise ValueError("type doit être image, zip ou pdf.")
    if media_source not in _ALLOWED_SOURCES:
        raise ValueError("source doit être upload ou generated.")

    aid = (asset_id or str(uuid.uuid4())).strip()
    now = _utc_now()
    tags_json = _normalize_tags(tags)

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO media_assets (
                    id, filename, type, mime_type, size_bytes, local_path,
                    r2_url, r2_key, project_id, source, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    aid,
                    clean_name,
                    media_type,
                    clean_mime,
                    max(0, int(size_bytes)),
                    clean_path,
                    r2_url.strip() if r2_url else None,
                    r2_key.strip() if r2_key else None,
                    project_id.strip() if project_id else None,
                    media_source,
                    tags_json,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM media_assets WHERE id = ?",
                (aid,),
            ).fetchone()
            result = _asset_from_row(row)
            if result is None:
                raise RuntimeError("Asset non retrouvé après insertion.")
            return result
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Asset déjà existant : {aid}") from exc
        finally:
            conn.close()


def get_asset(asset_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM media_assets WHERE id = ?",
                (asset_id.strip(),),
            ).fetchone()
            return _asset_from_row(row)
        finally:
            conn.close()


def list_assets(
    *,
    type: MediaType | None = None,
    project_id: str | None = None,
    source: MediaSource | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Liste les assets (filtres optionnels, recherche sur filename et tags)."""
    clauses: list[str] = []
    params: list[Any] = []

    if type:
        media_type = type.strip().lower()
        if media_type not in _ALLOWED_TYPES:
            raise ValueError("type doit être image, zip ou pdf.")
        clauses.append("type = ?")
        params.append(media_type)

    if project_id:
        clauses.append("project_id = ?")
        params.append(project_id.strip())

    if source:
        media_source = source.strip().lower()
        if media_source not in _ALLOWED_SOURCES:
            raise ValueError("source doit être upload ou generated.")
        clauses.append("source = ?")
        params.append(media_source)

    if search:
        term = f"%{search.strip().lower()}%"
        clauses.append(
            "(LOWER(filename) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(COALESCE(project_id, '')) LIKE ?)"
        )
        params.extend([term, term, term])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(int(limit), 1000))

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM media_assets
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, safe_limit),
            ).fetchall()
            assets = _rows_to_dicts(rows)
            for item in assets:
                item["tags"] = _parse_tags(item.get("tags"))
            return assets
        finally:
            conn.close()


def update_asset_r2(asset_id: str, r2_url: str, r2_key: str) -> dict[str, Any] | None:
    """Met à jour l'URL et la clé R2 après synchronisation."""
    clean_url = r2_url.strip()
    clean_key = r2_key.strip()
    if not clean_url or not clean_key:
        raise ValueError("r2_url et r2_key sont requis.")

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                UPDATE media_assets
                SET r2_url = ?, r2_key = ?
                WHERE id = ?
                """,
                (clean_url, clean_key, asset_id.strip()),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM media_assets WHERE id = ?",
                (asset_id.strip(),),
            ).fetchone()
            return _asset_from_row(row)
        finally:
            conn.close()


def delete_asset(asset_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM media_assets WHERE id = ?",
                (asset_id.strip(),),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def update_asset(
    asset_id: str,
    *,
    filename: str | None = None,
    project_id: str | None = None,
    tags: list[str] | str | None = None,
    clear_project_id: bool = False,
) -> dict[str, Any] | None:
    """Met à jour les métadonnées d'un asset."""
    updates: dict[str, Any] = {}
    if filename is not None:
        clean = filename.strip()
        if not clean:
            raise ValueError("filename ne peut pas être vide.")
        updates["filename"] = clean
    if clear_project_id:
        updates["project_id"] = None
    elif project_id is not None:
        updates["project_id"] = project_id.strip() if project_id.strip() else None
    if tags is not None:
        updates["tags"] = _normalize_tags(tags)

    if not updates:
        return get_asset(asset_id)

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [asset_id.strip()]

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE media_assets SET {set_clause} WHERE id = ?",
                params,
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM media_assets WHERE id = ?",
                (asset_id.strip(),),
            ).fetchone()
            return _asset_from_row(row)
        finally:
            conn.close()


def set_project_cover(project_key: str, media_asset_id: str) -> dict[str, Any]:
    key = project_key.strip()
    mid = media_asset_id.strip()
    if not key or not mid:
        raise ValueError("project_key et media_asset_id sont requis.")
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO project_cover_images (project_key, media_asset_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_key) DO UPDATE SET
                    media_asset_id = excluded.media_asset_id,
                    updated_at = excluded.updated_at
                """,
                (key, mid, now),
            )
            conn.commit()
            return {"project_key": key, "media_asset_id": mid, "updated_at": now}
        finally:
            conn.close()


def get_project_cover_media_id(project_key: str) -> str | None:
    key = project_key.strip()
    if not key:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT media_asset_id FROM project_cover_images WHERE project_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            return str(row[0]) if row[0] else None
        finally:
            conn.close()


def delete_project_cover(project_key: str) -> bool:
    key = project_key.strip()
    if not key:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM project_cover_images WHERE project_key = ?",
                (key,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
