"""
Routes démos client — création de liens partagés (usage interne / générateur).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.demos_store import (
    DemoDuration,
    DemoPayload,
    DemosStore,
    SupabaseStoreError,
    get_demos_store,
)
from security.cloudflare_env import cloudflare_configured, get_cloudflare_credentials
from tools.cloudflare_pages import (
    CloudflarePagesError,
    deploy_standalone_html,
    pages_project_name_for_token,
)
from tools.demo_preview_html import build_demo_preview_html

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demos"])


class DemoFileInput(BaseModel):
    path: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., max_length=500_000)


class CreateDemoRequest(BaseModel):
    duration: DemoDuration
    title: str | None = Field(default=None, max_length=200)
    files: list[DemoFileInput] = Field(..., min_length=1)
    stack: list[str] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=4000)
    project_type: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=500_000)
    generation_id: str | None = None


class CreateDemoResponse(BaseModel):
    id: str
    token: str
    password: str
    url: str
    unlock_url: str
    expires_at: str
    duration_hours: int
    title: str


def _unlock_demo_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_public_url.rstrip("/")
    return f"{base}/demo/{token}"


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    status = 502
    if detail.get("status_code") == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


@router.post("/demos", response_model=CreateDemoResponse)
async def create_client_demo(body: CreateDemoRequest) -> CreateDemoResponse:
    """Crée une démo client, déploie sur Cloudflare Pages si configuré dans .env."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Supabase non configuré — impossible de créer une démo.",
                "hint": "Configurez SUPABASE_URL et SUPABASE_SECRET_KEY.",
            },
        )

    if not cloudflare_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Cloudflare non configuré.",
                "hint": "Ajoutez CLOUDFLARE_ACCOUNT_ID et CLOUDFLARE_API_TOKEN dans backend/.env",
            },
        )

    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise HTTPException(status_code=503, detail="Cloudflare non configuré.")

    files = [{"path": f.path.strip(), "content": f.content} for f in body.files]
    if not files:
        raise HTTPException(status_code=422, detail="Au moins un fichier est requis.")

    title = (body.title or "").strip() or "Démo CyberForge"
    try:
        preview_html = build_demo_preview_html(
            files,
            title=title,
            code=body.code,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Impossible de générer l'aperçu HTML : {exc}",
        ) from exc

    demo_token = DemosStore._new_token()
    project_name = pages_project_name_for_token(demo_token)

    try:
        deploy = await deploy_standalone_html(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            project_name=project_name,
            html=preview_html,
        )
    except CloudflarePagesError as exc:
        logger.exception("Échec déploiement Cloudflare Pages")
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "hint": "Vérifiez le token API (permission Pages Write) et l'Account ID.",
            },
        ) from exc

    payload = DemoPayload(
        preview_html=preview_html,
        cloudflare_url=deploy.url,
        summary=body.summary,
        project_type=body.project_type,
    )

    try:
        created = await store.create_demo(
            title=title,
            payload=payload,
            duration=body.duration,
            generation_id=body.generation_id,
            token=demo_token,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /api/demos") from exc

    unlock_url = _unlock_demo_url(created.token)

    return CreateDemoResponse(
        id=created.id,
        token=created.token,
        password=created.password,
        url=deploy.url,
        unlock_url=unlock_url,
        expires_at=created.expires_at,
        duration_hours=created.duration_hours,
        title=created.title,
    )
