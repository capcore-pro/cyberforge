"""
Nettoyage externe lors de la suppression d'un projet pipeline (CoreMind /projects).
"""

from __future__ import annotations

import logging
from typing import Any

from db.demos_store import get_demos_store
from db.supabase_store import ProjectDetailResponse
from security.cloudflare_env import cloudflare_configured, get_cloudflare_credentials
from tools.cloudflare_pages import (
    CloudflarePagesError,
    pages_asset_path_for_token,
    pages_asset_path_legacy_for_token,
    remove_demo_from_cyberforge_demos,
)

logger = logging.getLogger(__name__)


async def cleanup_pipeline_project_externals(
    detail: ProjectDetailResponse,
) -> dict[str, Any]:
    """
    Retire les démos Cloudflare liées aux générations du projet et supprime
    les lignes `demos` (generation_id est seulement SET NULL en cascade).
    """
    demos_store = get_demos_store()
    linked_demos = []
    generation_ids = [g.id for g in detail.generations]

    if demos_store.is_configured():
        for generation_id in generation_ids:
            demo = await demos_store.find_by_generation_id(generation_id)
            if demo is not None:
                linked_demos.append(demo)

    report: dict[str, Any] = {
        "demos_removed": 0,
        "cloudflare_redeployed": False,
        "cloudflare_error": None,
        "cloudflare_skipped": None,
    }

    if not linked_demos:
        report["cloudflare_skipped"] = "Aucune démo liée"
        return report

    paths_to_remove: set[str] = set()
    for demo in linked_demos:
        cf_path = (demo.payload.cloudflare_path or "").strip()
        if cf_path:
            paths_to_remove.add(cf_path)
        paths_to_remove.add(pages_asset_path_legacy_for_token(demo.token))
        paths_to_remove.add(pages_asset_path_for_token(demo.token))

    has_cloudflare = bool(paths_to_remove)
    if has_cloudflare and cloudflare_configured():
        credentials = get_cloudflare_credentials()
        if credentials is None:
            report["cloudflare_skipped"] = "Credentials Cloudflare indisponibles"
            logger.warning(
                "DELETE projet %s: Cloudflare configuré mais credentials absents",
                detail.project.id,
            )
        else:
            try:
                remaining = await demos_store.list_cloudflare_manifest_entries()
                for path in paths_to_remove:
                    remaining.pop(path, None)
                result = await remove_demo_from_cyberforge_demos(
                    account_id=credentials.account_id,
                    api_token=credentials.api_token,
                    remaining_manifest_entries=remaining,
                )
                report["cloudflare_redeployed"] = True
                logger.info(
                    "DELETE projet %s: démo(s) retirée(s) de cyberforge-demos | "
                    "paths=%s | deployment_id=%s",
                    detail.project.id,
                    sorted(paths_to_remove),
                    result.deployment_id,
                )
            except CloudflarePagesError as exc:
                report["cloudflare_error"] = str(exc)
                logger.error(
                    "DELETE projet %s: échec retrait Cloudflare | paths=%s | %s",
                    detail.project.id,
                    sorted(paths_to_remove),
                    exc,
                )
    elif has_cloudflare:
        report["cloudflare_skipped"] = "Cloudflare non configuré"
        logger.info(
            "DELETE projet %s: retrait Cloudflare ignoré (non configuré)",
            detail.project.id,
        )

    if demos_store.is_configured():
        for demo in linked_demos:
            try:
                await demos_store.delete_demo(demo.id)
                report["demos_removed"] += 1
            except Exception as exc:
                logger.warning(
                    "DELETE projet %s: échec suppression démo %s | %s",
                    detail.project.id,
                    demo.id,
                    exc,
                )

    return report
