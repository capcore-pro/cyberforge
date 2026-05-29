"""
Persistance médiathèque — usage interne (Replicate, Unsplash, etc.).
"""

from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx

import media_db as db
from media_db import MediaSource, MediaType
from media_storage import (
    default_r2_key,
    get_local_url,
    save_local,
    sync_to_r2,
    update_asset_r2,
)

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

_ALLOWED_MIME: dict[str, tuple[MediaType, str]] = {
    "image/jpeg": ("image", "image/jpeg"),
    "image/png": ("image", "image/png"),
    "image/webp": ("image", "image/webp"),
    "image/gif": ("image", "image/gif"),
    "application/zip": ("zip", "application/zip"),
    "application/pdf": ("pdf", "application/pdf"),
}


def detect_media_type(content_type: str | None, filename: str) -> tuple[MediaType, str]:
    raw = (content_type or "").split(";")[0].strip().lower()
    if raw in _ALLOWED_MIME:
        return _ALLOWED_MIME[raw]

    guessed, _ = mimetypes.guess_type(filename)
    if guessed and guessed in _ALLOWED_MIME:
        return _ALLOWED_MIME[guessed]

    ext = Path(filename).suffix.lower()
    ext_map: dict[str, tuple[MediaType, str]] = {
        ".jpg": ("image", "image/jpeg"),
        ".jpeg": ("image", "image/jpeg"),
        ".png": ("image", "image/png"),
        ".webp": ("image", "image/webp"),
        ".gif": ("image", "image/gif"),
        ".zip": ("zip", "application/zip"),
        ".pdf": ("pdf", "application/pdf"),
    }
    if ext in ext_map:
        return ext_map[ext]

    raise ValueError(
        "Type de fichier non supporté. Acceptés : JPEG, PNG, WebP, GIF, ZIP, PDF."
    )


def _enrich_asset(asset: dict[str, Any]) -> dict[str, Any]:
    out = dict(asset)
    try:
        out["local_url"] = get_local_url(str(asset["local_path"]))
    except FileNotFoundError:
        out["local_url"] = f"/api/media/files/{asset['id']}"
    return out


async def save_generated_asset(
    url: str,
    filename: str,
    project_id: str | None,
    source: MediaSource,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Télécharge une ressource distante, persiste en local + DB, tente la sync R2.
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("url est requis.")

    media_source = source.strip().lower()
    if media_source not in ("upload", "generated"):
        raise ValueError("source doit être upload ou generated.")

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(clean_url)
    response.raise_for_status()
    file_bytes = response.content

    if len(file_bytes) > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"Fichier trop volumineux (max {MAX_DOWNLOAD_BYTES // (1024 * 1024)} Mo)."
        )

    content_type = response.headers.get("content-type")
    media_type, mime_type = detect_media_type(content_type, filename)

    asset_id = str(uuid.uuid4())
    local_path = save_local(file_bytes, filename, media_type)
    draft = {"id": asset_id, "filename": filename, "type": media_type}
    r2_key = default_r2_key(draft)

    asset = db.add_asset(
        filename=filename,
        type=media_type,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        local_path=local_path,
        source=media_source,  # type: ignore[arg-type]
        tags=tags,
        project_id=project_id,
        r2_key=r2_key,
        asset_id=asset_id,
    )

    r2_url = sync_to_r2(local_path, r2_key)
    if r2_url:
        updated = update_asset_r2(asset_id, r2_url, r2_key)
        if updated:
            asset = updated

    return _enrich_asset(asset)


async def try_save_generated_asset(
    url: str,
    filename: str,
    project_id: str | None,
    source: MediaSource,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    """Comme save_generated_asset mais ne bloque jamais le flux appelant."""
    try:
        return await save_generated_asset(
            url=url,
            filename=filename,
            project_id=project_id,
            source=source,
            tags=tags,
        )
    except Exception as exc:
        logger.warning(
            "Médiathèque — enregistrement ignoré (%s, project=%s): %s",
            filename,
            project_id,
            exc,
        )
        return None
