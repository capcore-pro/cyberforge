"""
Routes éditeur inline — lecture / sauvegarde HTML et redéploiement Cloudflare.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from config import get_settings
from db.audit_store import get_audit_store
from db.supabase_store import SupabaseStoreError, get_supabase_store
from media_storage import save_local, sync_to_r2
from tools.export_cloudflare import CloudflareExportError, deploy_html_demo
from tools.site_zip_export import build_site_export_zip
from tools.desktop_zip_export import build_desktop_package_zip
from tools.watermark import remove_watermark

logger = logging.getLogger(__name__)

router = APIRouter(tags=["editor"])

_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _not_configured_detail(store: Any) -> dict[str, Any]:
    diag = store.connection_diagnostics()
    return {
        "message": (
            "Supabase non configuré. Ajoutez SUPABASE_URL et "
            "SUPABASE_SECRET_KEY dans backend/.env."
        ),
        "diagnostics": diag,
    }


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    upstream = detail.pop("status_code", None)
    if upstream is not None:
        detail["upstream_status_code"] = upstream
    status = 502
    if upstream == 401:
        status = 401
    if "introuvable" in str(exc).lower():
        status = 404
    return HTTPException(status_code=status, detail=detail)


class EditorHtmlResponse(BaseModel):
    generation_id: str
    html: str
    demo_url: str | None = None
    project_title: str | None = None
    project_type: str | None = None
    is_desktop: bool = False
    electron_files: dict[str, str] | None = None


class SaveHtmlRequest(BaseModel):
    generation_id: str = Field(..., min_length=1)
    html: str = Field(..., min_length=1)


class SaveHtmlResponse(BaseModel):
    saved: bool = True


class RedeployRequest(BaseModel):
    generation_id: str = Field(..., min_length=1)
    html: str = Field(..., min_length=1)
    remove_watermark: bool = False


class RedeployResponse(BaseModel):
    url: str
    saved: bool = True


class UploadImageResponse(BaseModel):
    image_url: str


@router.get("/editor/{project_id}/html", response_model=EditorHtmlResponse)
async def get_editor_html(project_id: str) -> EditorHtmlResponse:
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        payload = await store.get_editor_html(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, f"GET /api/editor/{project_id}/html") from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="HTML introuvable pour ce projet.")

    return EditorHtmlResponse(
        generation_id=str(payload["generation_id"]),
        html=str(payload["html"]),
        demo_url=payload.get("demo_url"),
        project_title=payload.get("project_title"),
        project_type=payload.get("project_type"),
        is_desktop=bool(payload.get("is_desktop")),
        electron_files=payload.get("electron_files") or None,
    )


@router.get("/editor/{project_id}/export-zip")
async def export_editor_zip(project_id: str) -> Response:
    """Exporte le site complet en ZIP (index.html + assets CSS/JS + README)."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        payload = await store.get_editor_html(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"GET /api/editor/{project_id}/export-zip"
        ) from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="HTML introuvable pour ce projet.")

    html = str(payload.get("html") or "").strip()
    if not html:
        raise HTTPException(status_code=404, detail="HTML vide pour ce projet.")

    title = str(payload.get("project_title") or "projet")
    try:
        zip_bytes, filename = build_site_export_zip(
            html,
            title,
            remove_watermark=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/editor/{project_id}/download-desktop")
async def download_desktop_package(project_id: str) -> Response:
    """Télécharge le package Electron complet (index.html + fichiers build)."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        payload = await store.get_editor_html(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"GET /api/editor/{project_id}/download-desktop"
        ) from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    html = str(payload.get("html") or "").strip()
    if not html:
        raise HTTPException(status_code=404, detail="HTML vide pour ce projet.")

    electron_files = payload.get("electron_files")
    if not isinstance(electron_files, dict) or not electron_files:
        from agents.electron_ai import build_electron_files

        title = str(payload.get("project_title") or "CyberForge Desktop")
        electron_files = build_electron_files(title, app_name=title)

    title = str(payload.get("project_title") or "projet")
    try:
        zip_bytes, filename = build_desktop_package_zip(html, electron_files, title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/editor/{project_id}/html", response_model=SaveHtmlResponse)
async def save_editor_html(project_id: str, body: SaveHtmlRequest) -> SaveHtmlResponse:
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        before = await store.get_editor_html(project_id)
        html_before = str(before["html"]) if before else None
        await store.save_editor_html(
            project_id,
            body.generation_id.strip(),
            body.html,
            html_before=html_before,
            edit_type="manual_save",
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"PATCH /api/editor/{project_id}/html"
        ) from exc

    return SaveHtmlResponse(saved=True)


@router.post("/editor/{project_id}/redeploy", response_model=RedeployResponse)
async def redeploy_editor_html(project_id: str, body: RedeployRequest) -> RedeployResponse:
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        editor_ctx = await store.get_editor_html(project_id)
        if editor_ctx is None:
            raise HTTPException(status_code=404, detail="Projet introuvable.")

        html_before = str(editor_ctx.get("html") or "")
        project_type = str(editor_ctx.get("project_type") or "vitrine_next")
        title = str(editor_ctx.get("project_title") or "CyberForge")

        html_to_deploy = body.html.strip()
        if body.remove_watermark:
            html_to_deploy = remove_watermark(html_to_deploy)

        await store.save_editor_html(
            project_id,
            body.generation_id.strip(),
            html_to_deploy,
            html_before=html_before,
            edit_type="redeploy",
        )

        try:
            production_url, _token, _password, unlock_url = await deploy_html_demo(
                html=html_to_deploy,
                title=title,
                project_type=project_type,
            )
        except CloudflareExportError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        live_url = (unlock_url or production_url).strip().rstrip("/")
        await store.update_project_demo_url(project_id, live_url)

        await get_audit_store().log(
            "manual_edit_deployed",
            project_id=project_id,
            event_data={
                "generation_id": body.generation_id.strip(),
                "url": live_url,
            },
        )

        if body.remove_watermark:
            await get_audit_store().log(
                "watermark_removed",
                project_id=project_id,
                event_data={
                    "generation_id": body.generation_id.strip(),
                    "url": live_url,
                },
            )

        try:
            from agents.portal_onboarding_agent import notify_portal_client_site_updated

            notify_portal_client_site_updated(project_id, live_url)
        except Exception as e:
            logger.warning("Notification email échouée (non bloquant): %s", e)

        return RedeployResponse(url=live_url, saved=True)
    except HTTPException:
        raise
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"POST /api/editor/{project_id}/redeploy"
        ) from exc


@router.post("/editor/{project_id}/upload-image", response_model=UploadImageResponse)
async def upload_editor_image(
    project_id: str,
    file: UploadFile = File(...),
) -> UploadImageResponse:
    _ = project_id
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fichier requis.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Formats acceptés : jpg, png, webp, svg.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Taille max 5 Mo.")

    import media_db as db
    from media_router import _resolve_asset_public_url
    from media_storage import default_r2_key

    filename = Path(file.filename).name
    asset_id = str(uuid.uuid4())
    try:
        local_path = save_local(raw, filename, "image")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mime = file.content_type or "image/jpeg"
    r2_key = default_r2_key({"id": asset_id, "filename": filename, "type": "image"})
    try:
        asset = db.add_asset(
            filename=filename,
            type="image",
            mime_type=mime,
            size_bytes=len(raw),
            local_path=local_path,
            source="upload",
            tags=["editor"],
            project_id=project_id,
            r2_key=r2_key,
            asset_id=asset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    public_url = sync_to_r2(local_path, r2_key) or _resolve_asset_public_url(asset)
    return UploadImageResponse(image_url=public_url)
