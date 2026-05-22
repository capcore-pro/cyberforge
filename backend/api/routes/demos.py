"""
Routes démos client — création de liens partagés (usage interne / générateur).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.demo_password import generate_demo_password
from db.demos_store import (
    DemoDuration,
    DemoPayload,
    DemosStore,
    SupabaseStoreError,
    get_demos_store,
)
from security.cloudflare_env import cloudflare_configured, get_cloudflare_credentials
from tools.cloudflare_pages import (
    CYBERFORGE_DEMOS_PROJECT,
    CloudflarePagesError,
    LAST_CF_UPLOAD_HTML,
    demo_content_digest,
    deploy_demo_to_cyberforge_demos,
    pages_asset_path_for_token,
    public_demo_url_for_token,
    remove_demo_from_cyberforge_demos,
)
from tools.demo_preview_html import collect_standalone_sources
from tools.standalone_demo_html import build_standalone_demo_html, wrap_with_password_gate

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
    demo_token = DemosStore._new_token()
    demo_password = generate_demo_password()

    try:
        sources, static_html = collect_standalone_sources(files, code=body.code)
        if static_html:
            preview_html = wrap_with_password_gate(
                static_html,
                demo_password,
                title=title,
            )
        elif sources:
            preview_html = build_standalone_demo_html(
                sources,
                title=title,
                password=demo_password,
            )
        else:
            preview_html = build_standalone_demo_html(
                "",
                title=title,
                password=demo_password,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Impossible de générer l'aperçu HTML : {exc}",
        ) from exc

    try:
        other_entries = await store.list_cloudflare_manifest_entries(
            exclude_token=demo_token,
        )
        markers = {
            "cf-password-toggle": "cf-password-toggle" in preview_html,
            "cf-lock-btn": "cf-lock-btn" in preview_html,
        }
        logger.info(
            "POST /demos — HTML avant Cloudflare | bytes=%s | markers=%s",
            len(preview_html.encode("utf-8")),
            markers,
        )
        if not markers["cf-password-toggle"]:
            logger.warning(
                "POST /demos: cf-password-toggle absent du HTML généré — "
                "redémarrez uvicorn et régénérez la démo."
            )

        deploy = await deploy_demo_to_cyberforge_demos(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            token=demo_token,
            html=preview_html,
            other_manifest_entries=other_entries,
        )
        cf_path = deploy.asset_path or pages_asset_path_for_token(demo_token)
        cf_hash = deploy.content_hash
        if not cf_hash:
            _, cf_hash = demo_content_digest(demo_token, preview_html)
        logger.info(
            "POST /demos — déployé | cf_path=%s | cf_hash=%s | snapshot=%s",
            cf_path,
            cf_hash,
            LAST_CF_UPLOAD_HTML,
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
        cloudflare_url=public_demo_url_for_token(demo_token).rstrip("/"),
        cloudflare_path=cf_path,
        cloudflare_hash=cf_hash,
        cloudflare_project=CYBERFORGE_DEMOS_PROJECT,
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
            password=demo_password,
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


class DeleteDemoResponse(BaseModel):
    id: str
    deleted: bool
    cloudflare_redeployed: bool


@router.delete("/demos/{demo_id}", response_model=DeleteDemoResponse)
async def delete_client_demo(demo_id: str) -> DeleteDemoResponse:
    """Supprime la démo en base et retire son HTML du projet Pages cyberforge-demos."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(
            status_code=503,
            detail={"message": "Supabase non configuré."},
        )

    try:
        row = await store.get_by_id(demo_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "DELETE /api/demos/{id}") from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")

    cf_redeployed = False
    if row.payload.cloudflare_path and cloudflare_configured():
        credentials = get_cloudflare_credentials()
        if credentials is not None:
            remaining = await store.list_cloudflare_manifest_entries(
                exclude_token=row.token,
            )
            try:
                await remove_demo_from_cyberforge_demos(
                    account_id=credentials.account_id,
                    api_token=credentials.api_token,
                    remaining_manifest_entries=remaining,
                )
                cf_redeployed = True
            except CloudflarePagesError as exc:
                logger.exception("Échec retrait démo Cloudflare Pages")
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": str(exc),
                        "hint": "La démo n'a peut‑être pas été retirée de Pages.",
                    },
                ) from exc

    try:
        await store.delete_demo(demo_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "DELETE /api/demos/{id}") from exc

    return DeleteDemoResponse(
        id=demo_id,
        deleted=True,
        cloudflare_redeployed=cf_redeployed,
    )
