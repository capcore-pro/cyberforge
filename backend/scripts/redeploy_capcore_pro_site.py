"""Redéploie capcore-pro-site sur le projet Cloudflare Pages dédié capcore-pro-site."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config  # noqa: F401

from config import get_settings
from db.supabase_store import get_supabase_store
from security.cloudflare_env import get_cloudflare_credentials, load_cloudflare_from_env
from tools.deploy_manifest import slugify_project_name
from tools.export_cloudflare import deploy_dedicated_pages
from tools.theme_enforce import enforce_capcore_theme
import personal_projects_db as pp_db

PAGES_PROJECT = "capcore-pro-site"
PROJECT_TITLE = "capcore-pro-site"


async def _build_fallback_html(title: str, prompt: str) -> str:
    from dataclasses import replace

    from tools.demo_template_service import (
        TEMPLATE_LANDING,
        build_html_from_seed,
        heuristic_demo_seed,
    )

    seed = heuristic_demo_seed(
        prompt or f"Site vitrine {title} — CapCore Pro, agence digitale premium.",
        project_type_label="Site vitrine",
    )
    seed = replace(
        seed,
        template=TEMPLATE_LANDING,
        brand_name="CapCore Pro",
        title=title,
        subtitle="Solutions digitales sur mesure — déploiement Cloudflare Pages.",
    )
    return build_html_from_seed(seed)


async def main() -> None:
    load_cloudflare_from_env(get_settings())
    if get_cloudflare_credentials() is None:
        raise SystemExit("Cloudflare non configuré")

    store = get_supabase_store()
    preview = ""
    prompt = f"Site vitrine CapCore Pro — {PROJECT_TITLE}"

    if store.is_configured():
        projects = await store.list_projects(limit=100)
        for row in projects:
            if (row.title or "").strip().lower() == PROJECT_TITLE.lower():
                detail = await store.get_project(row.id)
                if detail and detail.generations:
                    gen = detail.generations[0]
                    preview = (gen.preview_html or gen.code or "").strip()
                    prompt = detail.project.prompt or prompt
                break

    if not preview:
        preview = await _build_fallback_html(PROJECT_TITLE, prompt)

    themed = enforce_capcore_theme(preview)
    slug = slugify_project_name(PAGES_PROJECT)
    url = await deploy_dedicated_pages(
        project_slug=slug,
        files={"index.html": themed},
        title=PROJECT_TITLE,
    )

    for row in pp_db.list_personal_projects():
        if (row.get("title") or "").strip().lower() == PROJECT_TITLE.lower():
            pp_db.update_personal_project(
                str(row["id"]),
                production_url=url,
                pages_project_slug=slug,
                demo_id=None,
            )

    print(f"OK dedicated project={slug} url={url}")


if __name__ == "__main__":
    asyncio.run(main())
