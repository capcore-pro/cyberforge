"""
Routes démos client — pipeline unique TaskFlow → Cloudflare.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.clients_store import MANUAL_DEMO_STATUSES, DemoStatusSlug, get_clients_store
from db.demo_password import generate_demo_password
from db.demos_store import (
    DemoDuration,
    DemoPayload,
    DemosStore,
    SupabaseStoreError,
    get_demos_store,
)
from tools.capcore_notify import send_capcore_contact_email
from tools.demo_password_vault import decrypt_demo_password, encrypt_demo_password
from tools.demo_urls import unlock_demo_url
from security.cloudflare_env import cloudflare_configured, get_cloudflare_credentials
from tools.cloudflare_pages import (
    CYBERFORGE_DEMOS_PROJECT,
    CloudflarePagesError,
    LAST_CF_UPLOAD_HTML,
    demo_content_digest,
    deploy_demo_to_cyberforge_demos,
    pages_asset_path_legacy_for_token,
    public_demo_url_for_token,
    remove_demo_from_cyberforge_demos,
)
from config import get_settings
from tools.demo_pipeline import (
    build_client_demo_document,
    client_demo_from_seed_dict,
    wrap_demo_for_cloudflare,
)
from tools.demo_template_service import heuristic_demo_seed, seed_as_dict
from tools.premium_seed_context import detect_demo_vertical
from tools.tavily_extract import TavilyError, tavily_extract_one

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
    client_id: str | None = None


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


class RedeployDemoPagesResponse(BaseModel):
    id: str
    token: str
    url: str
    content_hash: str | None = None


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


async def _seed_with_client_branding(
    demo_seed: dict | None,
    *,
    client_id: str | None,
) -> dict | None:
    if not client_id:
        return demo_seed
    clients = get_clients_store()
    if not clients.is_configured():
        return demo_seed
    try:
        client = await clients.get_by_id(client_id)
    except Exception:
        return demo_seed
    if client is None:
        return demo_seed

    merged: dict = dict(demo_seed) if isinstance(demo_seed, dict) else {}
    if client.primary_color and not merged.get("primary_color"):
        merged["primary_color"] = client.primary_color.strip()
    logo = (client.logo_url or "").strip()
    if logo.startswith("data:image/") and not merged.get("logo_data_url"):
        merged["logo_data_url"] = logo
    if client.company and not merged.get("brand_name"):
        merged["brand_name"] = client.company
    elif client.name and not merged.get("brand_name"):
        merged["brand_name"] = client.name
    return merged


class UrlClonePreviewRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    improved_prompt: str | None = Field(
        default=None,
        max_length=4000,
        description="Optionnel: consignes pour améliorer le clone (UX, copy, sections).",
    )


class UrlClonePreviewResponse(BaseModel):
    url: str
    vertical: str
    title: str
    html: str
    extracted_chars: int
    notes: list[str] = Field(default_factory=list)


def _domain_brand(url: str) -> str:
    import re
    from urllib.parse import urlparse

    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    host = re.sub(r"^www\.", "", host)
    if not host:
        return "Nova Studio"
    base = host.split(".")[0] if "." in host else host
    base = re.sub(r"[^a-z0-9-]+", " ", base).strip().replace("-", " ")
    return (base.title()[:40] or "Nova Studio").strip()


def _first_heading(markdown: str) -> str:
    for line in (markdown or "").splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return ""


@router.post("/demos/url-clone/preview", response_model=UrlClonePreviewResponse)
async def url_clone_preview(body: UrlClonePreviewRequest) -> UrlClonePreviewResponse:
    """
    Démo interne: analyse URL concurrente via Tavily (extract) puis génération d'un HTML premium.
    Ne déploie rien (pas de Cloudflare/Supabase) — sert uniquement à prévisualiser.
    """
    url = body.url.strip()
    improved = (body.improved_prompt or "").strip()
    notes: list[str] = []

    try:
        extracted = await tavily_extract_one(
            url,
            query="Proposition de valeur, sections, offres, tarifs, contact, témoignages, ton de marque",
            extract_depth="basic",
            include_images=True,
        )
    except TavilyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Tavily indisponible ou non configuré.",
                "error": str(exc),
                "hint": "Ajoutez TAVILY_API_KEY dans backend/.env",
            },
        ) from exc

    raw = extracted.raw_content.strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Extraction vide — impossible de cloner.")

    heading = _first_heading(raw)
    brand = _domain_brand(url)
    title = heading[:80].strip() or f"Site {brand}"
    vertical = detect_demo_vertical(raw + "\n" + improved, project_type_label="landing")

    # Seed “landing” enrichie: on injecte le contenu concurrent dans subtitle/prompt pour contextualiser.
    prompt = (
        f"Clone amélioré d'un concurrent depuis URL.\n"
        f"URL: {url}\n"
        f"Marque: {brand}\n"
        f"Vertical: {vertical}\n\n"
        f"Contenu extrait (markdown):\n{raw[:14_000]}\n\n"
    )
    if improved:
        prompt += f"Contraintes amélioration:\n{improved}\n"

    from tools.demo_template_service import DemoSeedData, align_seed_template
    from tools.demo_template_service import build_html_from_seed

    seed = DemoSeedData(
        template="landing",
        title=title,
        subtitle="Une expérience premium, plus claire, plus rapide, plus rassurante.",
        brand_name=brand,
        brand_tag="Version améliorée",
        user_name="Alex Martin",
        user_role="Fondateur",
        tasks=(),
        llm_personalized=False,
    )
    # Aligne la seed (vertical via hints) en réutilisant la pipeline existante.
    seed = align_seed_template(seed, prompt, project_type_label="landing")
    html = build_html_from_seed(seed)
    if "<!DOCTYPE" not in html or len(html) < 1000:
        raise HTTPException(status_code=422, detail="HTML généré invalide.")

    notes.append("Preview interne uniquement (aucun déploiement).")
    if extracted.images:
        notes.append(f"{len(extracted.images)} image(s) trouvée(s) (non injectées automatiquement en V1).")

    return UrlClonePreviewResponse(
        url=url,
        vertical=vertical,
        title=seed.title,
        html=html,
        extracted_chars=len(raw),
        notes=notes,
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

    seed_prompt = _seed_prompt(body, title) or title
    project_label = body.project_type or title

    merged_seed = await _seed_with_client_branding(
        body.demo_seed,
        client_id=body.client_id,
    )

    try:
        if merged_seed:
            document = client_demo_from_seed_dict(
                merged_seed,
                prompt=seed_prompt,
                project_type_label=project_label,
            )
        elif body.client_id:
            base_seed = seed_as_dict(
                heuristic_demo_seed(seed_prompt, project_type_label=project_label)
            )
            branded = await _seed_with_client_branding(
                base_seed,
                client_id=body.client_id,
            )
            document = client_demo_from_seed_dict(
                branded or base_seed,
                prompt=seed_prompt,
                project_type_label=project_label,
            )
        else:
            document = await build_client_demo_document(
                seed_prompt,
                project_type_label=project_label,
            )
        settings = get_settings()
        preview_html = wrap_demo_for_cloudflare(
            document,
            demo_password,
            title=title,
            demo_token=demo_token,
            demo_url=public_demo_url_for_token(demo_token),
            api_base_url=settings.demo_api_base_url,
        )
        logger.info(
            "POST /demos — DemoPipeline | template=%s | brand=%s | gated_bytes=%s",
            document.seed.template,
            document.seed.brand_name,
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
        cf_path = deploy.asset_path or pages_asset_path_legacy_for_token(demo_token)
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
        access_password_enc=encrypt_demo_password(demo_password),
    )

    try:
        created = await store.create_demo(
            title=title,
            payload=payload,
            duration=body.duration,
            generation_id=body.generation_id,
            client_id=body.client_id,
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
        unlock_url=unlock_demo_url(created.token),
        expires_at=created.expires_at,
        duration_hours=created.duration_hours,
        title=created.title,
    )


class DemoIdResponse(BaseModel):
    demo_id: str | None = None


@router.get(
    "/demos/by-generation/{generation_id}",
    response_model=DemoIdResponse,
)
async def demo_id_for_generation(generation_id: str) -> DemoIdResponse:
    """Identifiant de la démo client liée à une génération, si elle existe."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    try:
        row = await store.find_by_generation_id(generation_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /demos/by-generation/{id}") from exc

    return DemoIdResponse(demo_id=row.id if row else None)


class UpdateDemoStatusRequest(BaseModel):
    status: DemoStatusSlug = Field(
        ...,
        description="Statut manuel : validee ou expiree",
    )


class UpdateDemoStatusResponse(BaseModel):
    id: str
    status: DemoStatusSlug


class DemoOpenResponse(BaseModel):
    recorded: bool
    status: DemoStatusSlug


@router.get("/demos/{token}/open", response_model=DemoOpenResponse)
async def track_demo_open(token: str) -> DemoOpenResponse:
    """Tracking ouverture — passe le statut à « ouverte » si la démo était « envoyée »."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    clean = token.strip()
    row = await store.get_by_token(clean)
    if row is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")
    if store.is_expired(row):
        raise HTTPException(status_code=410, detail="Démo expirée.")

    updated = await store.record_open(clean)
    if updated is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")
    return DemoOpenResponse(
        recorded=updated.status == "ouverte",
        status=updated.status,
    )


class DemoInterestedRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=320)
    message: str = Field(..., min_length=1, max_length=8000)


class DemoInterestedResponse(BaseModel):
    recorded: bool
    status: DemoStatusSlug
    email_sent: bool = False


async def _handle_demo_interested(
    token: str,
    *,
    contact: DemoInterestedRequest | None,
) -> DemoInterestedResponse:
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    clean = token.strip()
    row = await store.get_by_token(clean)
    if row is None:
        logger.warning("demo interested — token inconnu: %s", clean)
        raise HTTPException(status_code=404, detail="Démo introuvable.")
    if store.is_expired(row):
        logger.info("demo interested — démo expirée: %s", clean)
        raise HTTPException(status_code=410, detail="Démo expirée.")

    interest = None
    if contact is not None:
        from db.demos_store import InterestContact

        interest = InterestContact(
            name=contact.name,
            email=contact.email,
            message=contact.message,
        )
        logger.info(
            "demo interested — soumission | token=%s | demo_id=%s | client=%s <%s>",
            clean,
            row.id,
            contact.name.strip(),
            contact.email.strip(),
        )

    try:
        updated = await store.record_interested(clean, contact=interest)
    except SupabaseStoreError as exc:
        logger.exception(
            "demo interested — échec Supabase PATCH | token=%s | detail=%s",
            clean,
            exc,
        )
        raise _http_error_from_supabase(exc, "PATCH /demos/interested") from exc

    if updated is None:
        logger.error("demo interested — record_interested sans ligne | token=%s", clean)
        raise HTTPException(status_code=404, detail="Démo introuvable.")

    email_sent = False
    if contact is not None:
        demo_url = (
            updated.payload.cloudflare_url or public_demo_url_for_token(clean)
        ).rstrip("/")
        demo_password = decrypt_demo_password(updated.payload.access_password_enc)
        email_sent = await send_capcore_contact_email(
            project_title=updated.title,
            client_name=contact.name,
            client_email=contact.email,
            message=contact.message,
            demo_url=demo_url,
            demo_password=demo_password,
            unlock_url=unlock_demo_url(clean),
        )
        logger.info(
            "demo interested — terminé | token=%s | status=%s | recorded=%s | email_sent=%s",
            clean,
            updated.status,
            updated.status == "interessee",
            email_sent,
        )

    return DemoInterestedResponse(
        recorded=updated.status == "interessee",
        status=updated.status,
        email_sent=email_sent,
    )


@router.post("/demos/{token}/interested", response_model=DemoInterestedResponse)
async def submit_demo_interested(
    token: str,
    body: DemoInterestedRequest,
) -> DemoInterestedResponse:
    """Formulaire CapCore soumis — statut, email Mat, notification CyberForge."""
    return await _handle_demo_interested(token, contact=body)


@router.get("/demos/{token}/interested", response_model=DemoInterestedResponse)
async def track_demo_interested(token: str) -> DemoInterestedResponse:
    """Compatibilité — enregistre le statut sans coordonnées client."""
    return await _handle_demo_interested(token, contact=None)


@router.patch("/demos/{demo_id}/status", response_model=UpdateDemoStatusResponse)
async def update_demo_status(
    demo_id: str,
    body: UpdateDemoStatusRequest,
) -> UpdateDemoStatusResponse:
    """Met à jour manuellement le statut (Validée / Expirée)."""
    if body.status not in MANUAL_DEMO_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Seuls les statuts « validee » et « expiree » sont modifiables manuellement.",
        )

    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    try:
        existing = await store.get_by_id(demo_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Démo introuvable.")
        updated = await store.update_status(demo_id, body.status)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "PATCH /demos/{id}/status") from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")
    return UpdateDemoStatusResponse(id=updated.id, status=updated.status)


@router.post("/demos/{demo_id}/redeploy-pages", response_model=RedeployDemoPagesResponse)
async def redeploy_demo_pages(demo_id: str) -> RedeployDemoPagesResponse:
    """Réinjecte token/API dans le HTML et republie sur Cloudflare Pages."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    if not cloudflare_configured():
        raise HTTPException(
            status_code=503,
            detail={"message": "Cloudflare non configuré."},
        )
    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise HTTPException(status_code=503, detail="Cloudflare non configuré.")

    try:
        row = await store.get_by_id(demo_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /demos/{id}/redeploy-pages") from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")

    preview_html = (row.payload.preview_html or "").strip()
    if not preview_html:
        raise HTTPException(status_code=422, detail="HTML de démo absent — recréez la démo.")

    try:
        other_entries = await store.list_cloudflare_manifest_entries(
            exclude_token=row.token,
        )
        deploy = await deploy_demo_to_cyberforge_demos(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            token=row.token,
            html=preview_html,
            other_manifest_entries=other_entries,
        )
    except CloudflarePagesError as exc:
        logger.exception("redeploy-pages — échec Cloudflare | demo_id=%s", demo_id)
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc

    public_url = public_demo_url_for_token(row.token).rstrip("/")
    logger.info(
        "redeploy-pages — OK | demo_id=%s | token=%s | hash=%s | snapshot=%s",
        demo_id,
        row.token,
        deploy.content_hash,
        LAST_CF_UPLOAD_HTML,
    )
    return RedeployDemoPagesResponse(
        id=row.id,
        token=row.token,
        url=public_url,
        content_hash=deploy.content_hash,
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
