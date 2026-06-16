"""
Export Cloudflare Pages — démos client (cyberforge-demos) et sites dédiés (*.pages.dev).
"""

from __future__ import annotations

import logging

from db.demo_password import generate_demo_password
from db.demos_store import DemosStore, get_demos_store
from security.cloudflare_env import get_cloudflare_credentials
from tools.cloudflare_pages import (
    CloudflarePagesError,
    deploy_dedicated_pages_site,
    deploy_demo_to_cyberforge_demos,
    pages_token_slug,
    public_demo_url_for_token,
    public_pages_url_for_project,
)
from tools.demo_urls import unlock_demo_url
from tools.generation_sources import is_usable_preview_html
from tools.standalone_demo_html import wrap_with_password_gate
from tools.theme_enforce import enforce_capcore_theme

logger = logging.getLogger(__name__)

_UNGATED_PROJECT_TYPES = frozenset(
    {"vitrine_next", "ecommerce", "site_reservation", "extension_navigateur"},
)
_GATED_PROJECT_TYPES = frozenset(
    {"application_web", "application_desktop", "real_app", "crm"},
)


def deploy_uses_password_gate(project_type: str | None) -> bool:
    """Vitrine / e-commerce / réservation : HTML public ; apps : gate mot de passe."""
    pt = (project_type or "").strip().lower()
    if pt in _UNGATED_PROJECT_TYPES:
        return False
    if pt in _GATED_PROJECT_TYPES:
        return True
    return True


class CloudflareExportError(Exception):
    """Échec export Cloudflare."""


def _files_to_bytes(files: dict[str, str]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path, content in files.items():
        clean_path = path.strip().lstrip("/").replace("\\", "/")
        if not clean_path:
            continue
        out[clean_path] = content.encode("utf-8")
    return out


async def deploy_dedicated_pages(
    *,
    project_slug: str,
    files: dict[str, str],
    title: str = "",
) -> str:
    """
    Déploie sur un projet Cloudflare Pages dédié (ex. capcore-pro-site.pages.dev).
    Retourne l'URL de production permanente.
    """
    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise CloudflareExportError("Cloudflare non configuré (CLOUDFLARE_*).")

    slug = project_slug.strip().lower()
    if not slug:
        raise CloudflareExportError("Slug projet Pages invalide.")

    upload_files = _files_to_bytes(files)
    if "index.html" not in upload_files:
        raise CloudflareExportError("index.html requis pour Cloudflare Pages dédié.")

    if "capcore" in slug or "capcore" in title.lower():
        html = upload_files["index.html"].decode("utf-8")
        upload_files["index.html"] = enforce_capcore_theme(html).encode("utf-8")

    index_bytes = upload_files.get("index.html", b"")
    logger.info(
        "[ExportAI] Déploiement slug=%s html_size=%s bytes",
        slug,
        len(index_bytes),
    )

    try:
        deploy = await deploy_dedicated_pages_site(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            project_name=slug,
            upload_files=upload_files,
        )
    except CloudflarePagesError as exc:
        raise CloudflareExportError(str(exc)) from exc

    url = (deploy.url or public_pages_url_for_project(slug)).rstrip("/")
    logger.info(
        "[Export Cloudflare] site dédié | project=%s | url=%s | files=%s",
        slug,
        url,
        sorted(upload_files.keys()),
    )
    return url


async def deploy_html_demo(
    *,
    html: str,
    title: str,
    project_type: str = "vitrine_next",
) -> tuple[str, str, str, str]:
    """
    Déploie le HTML sur Cloudflare Pages (cyberforge-demos, démo temporaire).
    Retourne (production_url, demo_token, demo_password, unlock_url).
    """
    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise CloudflareExportError("Cloudflare non configuré (CLOUDFLARE_*).")

    if not is_usable_preview_html(html):
        raise CloudflareExportError("HTML non déployable sur Cloudflare.")

    demo_token = DemosStore._new_token()
    use_gate = deploy_uses_password_gate(project_type)
    demo_password = ""
    upload_html = html.strip()
    if use_gate:
        demo_password = generate_demo_password()
        upload_html = wrap_with_password_gate(upload_html, demo_password, title=title)
        if "cf-password-toggle" not in upload_html:
            raise CloudflareExportError(
                "Gate mot de passe invalide (cf-password-toggle manquant)."
            )

    other_entries: dict[str, str] = {}
    store = get_demos_store()
    if store.is_configured():
        try:
            other_entries = await store.list_cloudflare_manifest_entries(
                exclude_token=demo_token,
            )
        except Exception as exc:
            logger.warning("Manifest Cloudflare Supabase ignoré : %s", exc)

    slug = pages_token_slug(demo_token)
    logger.info(
        "[ExportAI] Déploiement slug=%s gated=%s html_size=%s bytes",
        slug,
        use_gate,
        len(upload_html.encode("utf-8")),
    )

    try:
        deploy = await deploy_demo_to_cyberforge_demos(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            token=demo_token,
            html=upload_html,
            other_manifest_entries=other_entries,
            password_gated=use_gate,
        )
    except CloudflarePagesError as exc:
        raise CloudflareExportError(str(exc)) from exc

    production_url = (deploy.url or public_demo_url_for_token(demo_token)).rstrip("/")
    if not production_url.startswith("http"):
        production_url = public_demo_url_for_token(demo_token).rstrip("/")

    unlock = unlock_demo_url(demo_token) if use_gate else production_url
    return production_url, demo_token, demo_password, unlock


async def deploy_extension_demo(
    *,
    demo_html: str,
    zip_bytes: bytes,
    title: str,
    project_type: str = "extension_navigateur",
) -> tuple[str, str, str, str]:
    """
    Déploie la page de démo + extension.zip sur cyberforge-demos (même slug).
    """
    from tools.cloudflare_pages import pages_token_slug

    credentials = get_cloudflare_credentials()
    if credentials is None:
        raise CloudflareExportError("Cloudflare non configuré (CLOUDFLARE_*).")

    if not (demo_html or "").strip():
        raise CloudflareExportError("HTML de démo extension vide.")

    demo_token = DemosStore._new_token()
    slug = pages_token_slug(demo_token)
    zip_asset_path = f"d/{slug}/extension.zip"

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
        from tools.cloudflare_pages import deploy_demo_to_cyberforge_demos

        deploy = await deploy_demo_to_cyberforge_demos(
            account_id=credentials.account_id,
            api_token=credentials.api_token,
            token=demo_token,
            html=demo_html.strip(),
            other_manifest_entries=other_entries,
            password_gated=False,
            extra_upload_files={zip_asset_path: zip_bytes},
        )
    except Exception as exc:
        if isinstance(exc, CloudflareExportError):
            raise
        from tools.cloudflare_pages import CloudflarePagesError

        if isinstance(exc, CloudflarePagesError):
            raise CloudflareExportError(str(exc)) from exc
        raise CloudflareExportError(str(exc)) from exc

    production_url = (deploy.url or public_demo_url_for_token(demo_token)).rstrip("/")
    if not production_url.startswith("http"):
        production_url = public_demo_url_for_token(demo_token).rstrip("/")

    return production_url, demo_token, "", production_url
