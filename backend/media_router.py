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
import httpx

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


class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    project_id: str | None = Field(default=None, max_length=128)


class ImportUrlRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=4000)
    filename: str | None = Field(default=None, max_length=200)
    tags: list[str] | None = None
    project_id: str | None = Field(default=None, max_length=128)
    source: Literal["upload", "generated"] = "generated"


class UpdateAssetRequest(BaseModel):
    filename: str | None = Field(default=None, min_length=1, max_length=200)
    project_id: str | None = Field(default=None, max_length=128)
    tags: list[str] | None = None


class ProjectCoverRequest(BaseModel):
    media_asset_id: str = Field(..., min_length=1, max_length=128)


class ProjectCoverResponse(BaseModel):
    project_key: str
    media_asset_id: str | None = None
    asset: AssetResponse | None = None


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
        headers={"Cache-Control": "public, max-age=86400"},
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


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
async def patch_media_asset(asset_id: str, body: UpdateAssetRequest) -> AssetResponse:
    if body.filename is None and body.project_id is None and body.tags is None:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")
    try:
        updated = db.update_asset(
            asset_id,
            filename=body.filename,
            project_id=body.project_id,
            tags=body.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Asset introuvable.")
    return _asset_response(updated)


@router.post("/generate", response_model=AssetResponse, status_code=201)
async def generate_media_image(body: GenerateImageRequest) -> AssetResponse:
    """Génère une image via Replicate et l'enregistre localement."""
    from tools.replicate_image_gen import ReplicateImageGenerator
    from tools.replicate_screenshot import ReplicateScreenshotError

    generator = ReplicateImageGenerator()
    if not generator.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Replicate non configuré — ajoutez REPLICATE_API_KEY dans backend/.env.",
        )

    try:
        image_url = await generator.generate_image(
            body.prompt,
            project_id=body.project_id,
        )
    except ReplicateScreenshotError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("generate_media_image failed")
        raise HTTPException(status_code=502, detail=f"Génération Replicate échouée : {exc}") from exc

    if not image_url:
        raise HTTPException(
            status_code=502,
            detail="Replicate n'a pas renvoyé d'URL d'image. Vérifiez le modèle et la clé API.",
        )

    safe_name = f"replicate_{uuid.uuid4().hex[:12]}.png"
    try:
        asset = await save_generated_asset(
            image_url,
            safe_name,
            body.project_id,
            source="generated",
            tags=["replicate", "generated", "manual"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de télécharger l'image générée : {exc}",
        ) from exc

    return _asset_response(asset)


@router.post("/import-url", response_model=AssetResponse, status_code=201)
async def import_media_from_url(body: ImportUrlRequest) -> AssetResponse:
    """Télécharge une image distante (Pexels, Unsplash, etc.) en local."""
    filename = (body.filename or f"import_{uuid.uuid4().hex[:10]}.jpg").strip()
    try:
        asset = await save_generated_asset(
            body.url.strip(),
            filename,
            body.project_id,
            source=body.source,
            tags=body.tags or ["import"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Téléchargement impossible : {exc}",
        ) from exc

    return _asset_response(asset)


@router.get("/project-covers/{project_key}", response_model=ProjectCoverResponse)
async def get_project_cover(project_key: str) -> ProjectCoverResponse:
    media_id = db.get_project_cover_media_id(project_key)
    if not media_id:
        return ProjectCoverResponse(project_key=project_key, media_asset_id=None, asset=None)
    asset = db.get_asset(media_id)
    if asset is None:
        return ProjectCoverResponse(project_key=project_key, media_asset_id=None, asset=None)
    return ProjectCoverResponse(
        project_key=project_key,
        media_asset_id=media_id,
        asset=_asset_response(asset),
    )


@router.put("/project-covers/{project_key}", response_model=ProjectCoverResponse)
async def set_project_cover(project_key: str, body: ProjectCoverRequest) -> ProjectCoverResponse:
    asset = db.get_asset(body.media_asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset introuvable.")
    if str(asset.get("type")) != "image":
        raise HTTPException(status_code=400, detail="Seules les images peuvent servir de couverture.")
    try:
        db.set_project_cover(project_key, body.media_asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectCoverResponse(
        project_key=project_key,
        media_asset_id=body.media_asset_id,
        asset=_asset_response(asset),
    )


@router.delete("/project-covers/{project_key}")
async def clear_project_cover(project_key: str) -> dict[str, bool]:
    deleted = db.delete_project_cover(project_key)
    return {"deleted": deleted}


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
