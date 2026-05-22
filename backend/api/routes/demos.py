"""
Routes démos client — pipeline unique TaskFlow → Cloudflare.
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
from tools.demo_pipeline import (
    build_client_demo_document,
    client_demo_from_seed_dict,
    wrap_demo_for_cloudflare,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demos"])


class DemoFileInput(BaseModel):
    path: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., max_length=500_000)


class CreateDemoRequest(BaseModel):
    duration: DemoDuration
    title: str | None = Field(default=None, max_length=200)
    files: list[DemoFileInput] = Field(
        default_factory=list,
        description="Ignoré pour le HTML — conservé pour compat API.",
    )
    stack: list[str] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=4000)
    project_type: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=500_000)
    generation_id: str | None = None
    prompt: str | None = Field(default=None, max_length=8000)
    demo_seed: dict | None = None


class CreateDemoResponse(BaseModel):
    id: str
    token: str
    password: str
    url: str
    unlock_url: str
    expires_at: str
    duration_hours: int
    title: str


class DeleteDemoResponse(BaseModel):
    id: str
    deleted: bool
    cloudflare_redeployed: bool


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


def _seed_prompt(body: CreateDemoRequest, title: str) -> str:
    return "\n".join(
        p.strip()
        for p in (body.prompt or "", body.summary or "", body.project_type or "", title)
        if p and p.strip()
    )


@router.post("/demos", response_model=CreateDemoResponse)
async def create_client_demo(body: CreateDemoRequest) -> CreateDemoResponse:
    """Crée une démo : pipeline TaskFlow → gate → ZIP Cloudflare."""
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

    title = (body.title or "").strip() or "Démo CyberForge"
    demo_token = DemosStore._new_token()
    demo_password = generate_demo_password()

    try:
        if body.demo_seed:
            document = client_demo_from_seed_dict(body.demo_seed)
        else:
            document = await build_client_demo_document(
                _seed_prompt(body, title) or title,
                project_type_label=body.project_type or title,
            )
        preview_html = wrap_demo_for_cloudflare(
            document,
            demo_password,
            title=title,
        )
        logger.info(
            "POST /demos — DemoPipeline | brand=%s | tasks=%s | gated_bytes=%s",
            document.seed.brand_name,
            len(document.seed.tasks),
            len(preview_html.encode("utf-8")),
        )
    except (ValueError, Exception) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Pipeline démo : {exc}",
        ) from exc

    try:
        other_entries = await store.list_cloudflare_manifest_entries(
            exclude_token=demo_token,
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
            "POST /demos — déployé | cf_path=%s | snapshot=%s",
            cf_path,
            LAST_CF_UPLOAD_HTML,
        )
    except CloudflarePagesError as exc:
        logger.exception("Échec déploiement Cloudflare Pages")
        raise HTTPException(
            status_code=502,
            detail={"message": str(exc)},
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
        raise _http_error_from_supabase(exc, "POST /demos") from exc

    return CreateDemoResponse(
        id=created.id,
        token=created.token,
        password=created.password,
        url=deploy.url,
        unlock_url=_unlock_demo_url(created.token),
        expires_at=created.expires_at,
        duration_hours=created.duration_hours,
        title=created.title,
    )


@router.delete("/demos/{demo_id}", response_model=DeleteDemoResponse)
async def delete_client_demo(demo_id: str) -> DeleteDemoResponse:
    """Supprime la démo en base et retire son HTML du projet Pages cyberforge-demos."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    try:
        row = await store.get_by_id(demo_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "DELETE /demos/{id}") from exc

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
                raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc

    try:
        await store.delete_demo(demo_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "DELETE /demos/{id}") from exc

    return DeleteDemoResponse(
        id=demo_id,
        deleted=True,
        cloudflare_redeployed=cf_redeployed,
    )
