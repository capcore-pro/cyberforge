"""
Export Cloudflare Pages — déploiement démo client (projet cyberforge-demos).
"""

from __future__ import annotations

import logging

from db.demo_password import generate_demo_password
from db.demos_store import DemosStore, get_demos_store
from security.cloudflare_env import get_cloudflare_credentials
from tools.cloudflare_pages import (
    CloudflarePagesError,
    deploy_demo_to_cyberforge_demos,
    public_demo_url_for_token,
)
from tools.demo_urls import unlock_demo_url
from tools.generation_sources import is_usable_preview_html
from tools.standalone_demo_html import wrap_with_password_gate

logger = logging.getLogger(__name__)


class CloudflareExportError(Exception):
    """Échec export Cloudflare."""


async def deploy_html_demo(
    *,
    html: str,
    title: str,
) -> tuple[str, str, str, str]:
    """
    Déploie le HTML sur Cloudflare Pages.
    Retourne (production_url, demo_token, demo_password, unlock_url).
    """
    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise CloudflareExportError("Cloudflare non configuré (CLOUDFLARE_*).")

    if not is_usable_preview_html(html):
        raise CloudflareExportError("HTML non déployable sur Cloudflare.")

    demo_token = DemosStore._new_token()
    demo_password = generate_demo_password()
    gated = wrap_with_password_gate(html.strip(), demo_password, title=title)
    if "cf-password-toggle" not in gated:
        raise CloudflareExportError("Gate mot de passe invalide (cf-password-toggle manquant).")

    other_entries: dict[str, str] = {}
    store = get_demos_store()
    if store.is_configured():
        try:
            other_entries = await store.list_cloudflare_manifest_entries(
                exclude_token=demo_token,
            )
        except Exception as exc:
            logger.warning("Manifest Cloudflare Supabase ignoré : %s", exc)

    try:
        deploy = await deploy_demo_to_cyberforge_demos(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            token=demo_token,
            html=gated,
            other_manifest_entries=other_entries,
        )
    except CloudflarePagesError as exc:
        raise CloudflareExportError(str(exc)) from exc

    production_url = (deploy.url or public_demo_url_for_token(demo_token)).rstrip("/")
    if not production_url.startswith("http"):
        production_url = public_demo_url_for_token(demo_token).rstrip("/")

    unlock = unlock_demo_url(demo_token)
    return production_url, demo_token, demo_password, unlock
