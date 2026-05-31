"""
Persistance Supabase d'une démo après ExportAI (Cloudflare Pages).

ExportAI déploie sur cyberforge-demos mais ne créait pas de ligne `demos`,
ce qui laissait les projets Supabase en statut « Hors ligne » sans URL.
"""

from __future__ import annotations

import logging

from agents.coremind_agent import CoreMindRunResult
from config import get_settings
from db.demo_password import generate_demo_password
from db.demos_store import DemoDuration, DemoPayload, get_demos_store
from tools.cloudflare_pages import (
    CYBERFORGE_DEMOS_PROJECT,
    demo_content_digest,
    pages_asset_path_legacy_for_token,
    public_demo_url_for_token,
)
from tools.demo_password_vault import encrypt_demo_password
from tools.demo_runtime import ensure_demo_runtime_config, extract_demo_title_from_html
from tools.demo_urls import unlock_demo_url
from tools.standalone_demo_html import wrap_with_password_gate
from tools.theme_enforce import enforce_capcore_theme

logger = logging.getLogger(__name__)


async def persist_pipeline_cloudflare_demo(
    *,
    run_result: CoreMindRunResult,
    generation_id: str,
    duration: DemoDuration = "7d",
    client_id: str | None = None,
) -> str | None:
    """
    Enregistre la démo Cloudflare déjà déployée par ExportAI dans Supabase.

    Retourne l'identifiant démo ou None si rien à persister.
    """
    token = (run_result.demo_token or "").strip()
    password = (run_result.demo_password or "").strip()
    production_url = (run_result.production_url or "").strip()
    if not token or not production_url:
        return None
    if run_result.export_provider not in (None, "cloudflare"):
        return None

    store = get_demos_store()
    if not store.is_configured():
        logger.warning("persist_pipeline_cloudflare_demo: Supabase non configuré")
        return None

    existing = await store.find_by_generation_id(generation_id)
    if existing is not None:
        logger.info(
            "persist_pipeline_cloudflare_demo: démo déjà liée | generation=%s demo=%s",
            generation_id,
            existing.id,
        )
        return existing.id

    preview = (run_result.preview_html or run_result.generation.code or "").strip()
    if not preview:
        logger.warning(
            "persist_pipeline_cloudflare_demo: HTML vide | generation=%s",
            generation_id,
        )
        return None

    title = (
        run_result.architect_plan.project_type_label
        or run_result.analysis.project_type_label
        or "Démo CyberForge"
    )
    if "capcore" in title.lower() or "capcore" in preview[:4000].lower():
        preview = enforce_capcore_theme(preview)
    demo_password = password or generate_demo_password()
    gated = wrap_with_password_gate(preview, demo_password, title=title)
    settings = get_settings()
    gated = ensure_demo_runtime_config(
        gated,
        token=token,
        project_title=extract_demo_title_from_html(gated) or title,
        demo_url=public_demo_url_for_token(token),
        api_base_url=settings.demo_api_base_url,
    )
    cf_path = pages_asset_path_legacy_for_token(token)
    _, cf_hash = demo_content_digest(token, gated)
    url = public_demo_url_for_token(token).rstrip("/")

    payload = DemoPayload(
        preview_html=gated,
        cloudflare_url=url,
        cloudflare_path=cf_path,
        cloudflare_hash=cf_hash,
        cloudflare_project=CYBERFORGE_DEMOS_PROJECT,
        summary=run_result.generation.summary,
        project_type=run_result.analysis.project_type.value,
        access_password_enc=encrypt_demo_password(demo_password),
    )

    try:
        created = await store.create_demo(
            title=title,
            payload=payload,
            duration=duration,
            generation_id=generation_id,
            client_id=client_id,
            token=token,
            password=demo_password,
        )
    except Exception as exc:
        logger.warning(
            "persist_pipeline_cloudflare_demo: échec création démo | generation=%s | %s",
            generation_id,
            exc,
        )
        return None

    logger.info(
        "persist_pipeline_cloudflare_demo: OK | demo=%s url=%s unlock=%s",
        created.id,
        url,
        unlock_demo_url(token),
    )
    return created.id
