"""
CMS Client (P18) — authentification client, édition de contenu et publication.

Routes montées sous /api/cms via main.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings, plain_secret_str
from db.cms_store import get_cms_content_store
from db.managed_projects_store import get_managed_projects_store
from tools.cms_content_blocks import extract_blocks_from_site_json
from tools.cms_jwt import CmsJwtError, create_cms_token, decode_cms_token
from tools.cms_publish import schedule_cms_publish
from tools.cms_project_settings import build_cms_login_url
from tools.export_github import get_github_file
from tools.vitrine_auth_service import decrypt_password

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms"])
panel_router = APIRouter(tags=["cms-panel"])

CMS_PANEL_PATH = (
    Path(__file__).resolve().parent.parent.parent / "templates" / "cms-panel" / "cms-panel.js"
)

CMS_COOKIE = "cms_session"
CMS_COOKIE_PATH = "/api/cms"
CMS_COOKIE_MAX_AGE = 7 * 24 * 3600


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


class CmsLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=250)
    password: str = Field(..., min_length=1, max_length=200)


class CmsLoginResponse(BaseModel):
    ok: bool
    project_id: str
    email: str
    token: str


class CmsMeResponse(BaseModel):
    project_id: str
    email: str
    title: str | None = None
    slug: str | None = None
    status: str | None = None
    url_production: str | None = None
    type: str | None = None


class CmsContentBlock(BaseModel):
    block_key: str
    block_type: str
    value: Any = None
    updated_at: str | None = None


class CmsContentResponse(BaseModel):
    project_id: str
    blocks: list[CmsContentBlock]


class CmsContentPatchRequest(BaseModel):
    blocks: list[CmsContentBlock] = Field(min_length=1)


class CmsPublishResponse(BaseModel):
    scheduled: bool
    job_id: str
    run_id: str
    message: str


class CmsProjectSettingsResponse(BaseModel):
    project_id: str
    cms_enabled: bool
    cms_login_url: str | None = None
    site_url: str | None = None


class CmsProjectSettingsPatch(BaseModel):
    cms_enabled: bool


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _jwt_secret() -> str:
    return plain_secret_str(get_settings().secret_key)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    secure = settings.app_env.lower() in ("production", "prod")
    response.set_cookie(
        key=CMS_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=CMS_COOKIE_MAX_AGE,
        path=CMS_COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=CMS_COOKIE, path=CMS_COOKIE_PATH)


def _read_session_token(request: Request) -> str | None:
    token = request.cookies.get(CMS_COOKIE)
    return token.strip() if token and token.strip() else None


def _session_from_request(request: Request, token_query: str | None = None) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization") or ""
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer:
            try:
                return decode_cms_token(bearer, _jwt_secret())
            except CmsJwtError as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
    if token_query and token_query.strip():
        try:
            return decode_cms_token(token_query.strip(), _jwt_secret())
        except CmsJwtError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    token = _read_session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié.")
    try:
        return decode_cms_token(token, _jwt_secret())
    except CmsJwtError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _require_project_access(request: Request, project_id: str) -> dict[str, Any]:
    session = _session_from_request(request)
    if session.get("sub") != project_id:
        raise HTTPException(status_code=403, detail="Accès refusé à ce projet.")
    return session


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _project_site_url(row: Any) -> str | None:
    return (
        (row.url_production or "").strip()
        or (row.url_preview or "").strip()
        or None
    )


async def _get_managed_or_404(project_id: str) -> Any:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    project = await store.get_project(project_id)
    if not project or project.deleted_at:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return project


async def _ensure_cms_enabled(project_id: str) -> Any:
    project = await _get_managed_or_404(project_id)
    if not bool(getattr(project, "cms_enabled", True)):
        raise HTTPException(status_code=403, detail="Mode CMS désactivé pour ce projet.")
    return project


# ---------------------------------------------------------------------------
# Paramètres projet (CyberForge UI)
# ---------------------------------------------------------------------------


@router.get("/cms/projects/{project_id}/settings", response_model=CmsProjectSettingsResponse)
async def cms_project_settings(project_id: str) -> CmsProjectSettingsResponse:
    project = await _get_managed_or_404(project_id)
    site_url = _project_site_url(project)
    enabled = bool(getattr(project, "cms_enabled", True))
    login_url = build_cms_login_url(site_url) if enabled and site_url else None
    return CmsProjectSettingsResponse(
        project_id=project_id,
        cms_enabled=enabled,
        cms_login_url=login_url,
        site_url=site_url,
    )


@router.patch("/cms/projects/{project_id}/settings", response_model=CmsProjectSettingsResponse)
async def cms_patch_project_settings(
    project_id: str,
    body: CmsProjectSettingsPatch,
) -> CmsProjectSettingsResponse:
    store = get_managed_projects_store()
    project = await _get_managed_or_404(project_id)
    updated = await store.update_project(
        project_id,
        patch={"cms_enabled": bool(body.cms_enabled)},
    )
    site_url = _project_site_url(updated)
    enabled = bool(getattr(updated, "cms_enabled", True))
    login_url = build_cms_login_url(site_url) if enabled and site_url else None
    return CmsProjectSettingsResponse(
        project_id=project_id,
        cms_enabled=enabled,
        cms_login_url=login_url,
        site_url=site_url,
    )


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@router.post("/cms/login", response_model=CmsLoginResponse)
async def cms_login(body: CmsLoginRequest, response: Response) -> CmsLoginResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    email = body.email.strip().lower()
    password = body.password.strip()
    candidates = await store.list_auth_by_email(email)
    if not candidates:
        raise HTTPException(status_code=401, detail="Identifiants invalides.")

    matched_project_id: str | None = None
    for auth in candidates:
        expected = decrypt_password(auth) or ""
        if password == expected:
            matched_project_id = auth.project_id
            break

    if not matched_project_id:
        raise HTTPException(status_code=401, detail="Identifiants invalides.")

    project = await store.get_project(matched_project_id)
    if not project or project.deleted_at:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if not bool(getattr(project, "cms_enabled", True)):
        raise HTTPException(status_code=403, detail="Mode CMS désactivé pour ce projet.")

    token = create_cms_token(
        project_id=matched_project_id,
        email=email,
        secret=_jwt_secret(),
        ttl_seconds=CMS_COOKIE_MAX_AGE,
    )
    _set_session_cookie(response, token)
    return CmsLoginResponse(
        ok=True,
        project_id=matched_project_id,
        email=email,
        token=token,
    )


@router.post("/cms/logout")
async def cms_logout(response: Response) -> dict[str, bool]:
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/cms/me", response_model=CmsMeResponse)
async def cms_me(request: Request) -> CmsMeResponse:
    session = _session_from_request(request)
    project_id = str(session.get("sub") or "")
    project = await _ensure_cms_enabled(project_id)
    return CmsMeResponse(
        project_id=project_id,
        email=str(session.get("email") or ""),
        title=project.title,
        slug=project.slug,
        status=project.status,
        url_production=project.url_production,
        type=project.type,
    )


# ---------------------------------------------------------------------------
# Contenu
# ---------------------------------------------------------------------------


async def _load_merged_blocks(project_id: str) -> list[CmsContentBlock]:
    store = get_managed_projects_store()
    cms = get_cms_content_store()
    project = await store.get_project(project_id)
    if not project or project.deleted_at:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    merged: dict[str, CmsContentBlock] = {}

    if project.github_repo and project.github_branch:
        try:
            settings = get_settings()
            _sha, raw = await get_github_file(
                repo=project.github_repo,
                branch=project.github_branch,
                path="content/site.json",
                settings=settings,
            )
            for item in extract_blocks_from_site_json(raw):
                merged[item["block_key"]] = CmsContentBlock(
                    block_key=item["block_key"],
                    block_type=item["block_type"],
                    value=item["value"],
                    updated_at=None,
                )
        except Exception:
            logger.debug("CMS: site.json indisponible pour %s", project_id, exc_info=True)

    for row in await cms.list_blocks(project_id):
        merged[row.block_key] = CmsContentBlock(
            block_key=row.block_key,
            block_type=row.block_type,
            value=row.value,
            updated_at=row.updated_at,
        )

    return sorted(merged.values(), key=lambda b: b.block_key)


@router.get("/cms/{project_id}/content", response_model=CmsContentResponse)
async def cms_get_content(project_id: str, request: Request) -> CmsContentResponse:
    _require_project_access(request, project_id)
    await _ensure_cms_enabled(project_id)
    blocks = await _load_merged_blocks(project_id)
    return CmsContentResponse(project_id=project_id, blocks=blocks)


@router.patch("/cms/{project_id}/content", response_model=CmsContentResponse)
async def cms_patch_content(
    project_id: str,
    body: CmsContentPatchRequest,
    request: Request,
) -> CmsContentResponse:
    _require_project_access(request, project_id)
    await _ensure_cms_enabled(project_id)
    cms = get_cms_content_store()
    if not cms.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    payload = [
        {
            "block_key": block.block_key,
            "block_type": block.block_type,
            "value": block.value,
        }
        for block in body.blocks
    ]
    await cms.upsert_blocks(project_id, payload)
    blocks = await _load_merged_blocks(project_id)
    return CmsContentResponse(project_id=project_id, blocks=blocks)


# ---------------------------------------------------------------------------
# Publication + SSE
# ---------------------------------------------------------------------------


@router.post("/cms/{project_id}/publish", response_model=CmsPublishResponse)
async def cms_publish(project_id: str, request: Request) -> CmsPublishResponse:
    _require_project_access(request, project_id)
    await _ensure_cms_enabled(project_id)
    try:
        result = await schedule_cms_publish(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cms_publish")
        raise HTTPException(status_code=500, detail="Publication impossible.") from exc

    return CmsPublishResponse(
        scheduled=bool(result.get("scheduled")),
        job_id=str(result.get("job_id", "")),
        run_id=str(result.get("run_id", "")),
        message=str(result.get("message", "Publication en cours")),
    )


@router.get("/cms/publish/{job_id}/stream")
async def cms_publish_stream(
    job_id: str,
    request: Request,
    token: str | None = Query(default=None),
) -> StreamingResponse:
    """SSE — suivi d'un job de publication CMS (même format que le pipeline)."""
    session = _session_from_request(request, token_query=token)
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    run = await store.get_run(job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job introuvable.")
    if session.get("sub") != run.project_id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    async def event_generator() -> AsyncIterator[str]:
        yield _sse_line(
            {
                "type": "pipeline_start",
                "agent": "cms",
                "message": "Publication CMS démarrée",
                "job_id": job_id,
            }
        )
        yield _sse_line(
            {
                "type": "step_start",
                "agent": "cms",
                "step": "publish",
                "message": "Injection du contenu et redéploiement…",
            }
        )

        last_status: str | None = None
        for _ in range(150):
            current = await store.get_run(job_id)
            if not current:
                yield _sse_line({"type": "error", "detail": "Job introuvable."})
                return
            if current.status != last_status:
                last_status = current.status
                if current.status == "running":
                    yield _sse_line(
                        {
                            "type": "step_start",
                            "agent": "cms",
                            "step": "deploy",
                            "message": "Redéploiement en cours…",
                        }
                    )
            if current.status in ("succeeded", "failed"):
                yield _sse_line(
                    {
                        "type": "step_done",
                        "agent": "cms",
                        "step": "publish",
                        "ok": current.status == "succeeded",
                        "message": current.error or "Publication terminée.",
                        "artifacts": current.artifacts,
                    }
                )
                if current.status == "succeeded":
                    project = await store.get_project(current.project_id)
                    yield _sse_line(
                        {
                            "type": "result",
                            "data": {
                                "job_id": job_id,
                                "project_id": current.project_id,
                                "url_production": project.url_production if project else None,
                                "artifacts": current.artifacts,
                            },
                        }
                    )
                else:
                    yield _sse_line(
                        {
                            "type": "error",
                            "detail": current.error or "Échec publication CMS.",
                        }
                    )
                return
            await asyncio.sleep(2.0)

        yield _sse_line({"type": "error", "detail": "Délai de suivi dépassé."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@panel_router.get("/cms/panel.js")
async def cms_panel_script() -> FileResponse:
    """Script panneau CMS client — injecté dans les sites générés."""
    if not CMS_PANEL_PATH.is_file():
        raise HTTPException(status_code=404, detail="cms-panel.js introuvable.")
    return FileResponse(
        CMS_PANEL_PATH,
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )
