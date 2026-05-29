"""
API médiathèque — upload, fichiers locaux, sync R2.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import media_db as db
from media_db import MediaSource, MediaType
from media_storage import (
    default_r2_key,
    delete_from_r2,
    delete_local,
    get_local_url,
    save_local,
    sync_all_pending,
    sync_to_r2,
    update_asset_r2,
)
from tools.media_library import (
    detect_media_type,
    save_generated_asset,
    try_save_generated_asset,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class AssetResponse(BaseModel):
    id: str
    filename: str
    type: str
    mime_type: str
    size_bytes: int
    local_path: str
    local_url: str | None = None
    r2_url: str | None = None
    r2_key: str | None = None
    project_id: str | None = None
    source: str
    tags: list[str] = Field(default_factory=list)
    created_at: str


class SyncR2Response(BaseModel):
    status: str = "started"
    message: str | None = None


def _enrich_asset(asset: dict[str, Any]) -> dict[str, Any]:
    out = dict(asset)
    try:
        out["local_url"] = get_local_url(str(asset["local_path"]))
    except FileNotFoundError:
        out["local_url"] = f"/api/media/files/{asset['id']}"
    return out


def _asset_response(asset: dict[str, Any]) -> AssetResponse:
    return AssetResponse(**_enrich_asset(asset))


def _mime_to_media_type(content_type: str | None, filename: str) -> tuple[MediaType, str]:
    try:
        return detect_media_type(content_type, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _parse_tags_form(raw: str | None) -> list[str] | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="tags JSON invalide.") from exc
    return [t.strip() for t in text.split(",") if t.strip()]


def _background_sync_asset(asset_id: str, local_path: str, r2_key: str) -> None:
    try:
        url = sync_to_r2(local_path, r2_key)
        if url:
            update_asset_r2(asset_id, url, r2_key)
    except Exception:
        logger.exception("Sync R2 arrière-plan échouée pour %s", asset_id)


def sync_asset_by_id(asset_id: str) -> dict[str, Any] | None:
    """Sync R2 pour un asset (usage route + interne)."""
    asset = db.get_asset(asset_id)
    if asset is None:
        return None
    local_path = str(asset.get("local_path") or "")
    if not local_path or not Path(local_path).is_file():
        return None
    r2_key = (asset.get("r2_key") or "").strip() or default_r2_key(asset)
    url = sync_to_r2(local_path, r2_key)
    if not url:
        return asset
    return update_asset_r2(asset_id, url, r2_key)


def _delete_asset_full(asset_id: str) -> bool:
    asset = db.get_asset(asset_id)
    if asset is None:
        return False
    delete_local(str(asset.get("local_path") or ""))
    r2_key = asset.get("r2_key")
    if r2_key:
        delete_from_r2(str(r2_key))
    return db.delete_asset(asset_id)


@router.post("/upload", response_model=AssetResponse, status_code=201)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str | None = Form(None),
    tags: str | None = Form(None),
) -> AssetResponse:
    """Upload multipart → disque + DB ; sync R2 en arrière-plan."""
    filename = file.filename or "upload.bin"
    content_type = file.content_type

    chunks: list[bytes] = []
    total = 0
    while True:
        block = await file.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo).",
            )
        chunks.append(block)

    file_bytes = b"".join(chunks)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    media_type, mime_type = _mime_to_media_type(content_type, filename)
    parsed_tags = _parse_tags_form(tags)

    asset_id = str(uuid.uuid4())
    try:
        local_path = save_local(file_bytes, filename, media_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    draft = {"id": asset_id, "filename": filename, "type": media_type}
    r2_key = default_r2_key(draft)

    try:
        asset = db.add_asset(
            filename=filename,
            type=media_type,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            local_path=local_path,
            source="upload",
            tags=parsed_tags,
            project_id=project_id,
            r2_key=r2_key,
            asset_id=asset_id,
        )
    except ValueError as exc:
        delete_local(local_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(_background_sync_asset, asset_id, local_path, r2_key)
    return _asset_response(asset)


@router.get("/files/{asset_id}")
async def serve_local_file(asset_id: str) -> FileResponse:
    asset = db.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset introuvable.")

    path = Path(str(asset["local_path"]))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier local absent.")

    return FileResponse(
        path,
        media_type=str(asset.get("mime_type") or "application/octet-stream"),
        filename=str(asset.get("filename") or path.name),
    )


@router.get("/assets", response_model=list[AssetResponse])
async def list_media_assets(
    type: MediaType | None = Query(None),
    source: MediaSource | None = Query(None),
    project_id: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
) -> list[AssetResponse]:
    try:
        rows = db.list_assets(
            type=type,
            source=source,
            project_id=project_id,
            search=search,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [_asset_response(row) for row in rows]


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_media_asset(asset_id: str) -> AssetResponse:
    asset = db.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset introuvable.")
    return _asset_response(asset)


@router.delete("/assets/{asset_id}")
async def delete_media_asset(asset_id: str) -> dict[str, str]:
    if not _delete_asset_full(asset_id):
        raise HTTPException(status_code=404, detail="Asset introuvable.")
    return {"status": "deleted", "asset_id": asset_id}


@router.post("/sync-r2", response_model=SyncR2Response)
async def trigger_sync_all_r2(background_tasks: BackgroundTasks) -> SyncR2Response:
    background_tasks.add_task(sync_all_pending)
    return SyncR2Response(
        status="started",
        message="Synchronisation R2 globale lancée en arrière-plan.",
    )


@router.post("/assets/{asset_id}/sync-r2", response_model=AssetResponse)
async def trigger_sync_asset_r2(
    asset_id: str,
    background_tasks: BackgroundTasks,
    sync_now: bool = Query(False, description="Si true, sync synchrone (défaut : arrière-plan)."),
) -> AssetResponse:
    asset = db.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset introuvable.")

    if sync_now:
        updated = sync_asset_by_id(asset_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Asset introuvable.")
        return _asset_response(updated)

    local_path = str(asset.get("local_path") or "")
    r2_key = (asset.get("r2_key") or "").strip() or default_r2_key(asset)
    background_tasks.add_task(_background_sync_asset, asset_id, local_path, r2_key)
    return _asset_response(asset)


__all__ = [
    "router",
    "save_generated_asset",
    "try_save_generated_asset",
    "sync_asset_by_id",
]
