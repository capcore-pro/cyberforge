"""Publication CMS — injection contenu dans GitHub + redéploiement Vercel."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from config import get_settings
from db.cms_store import get_cms_content_store
from db.managed_projects_store import get_managed_projects_store
from tools.cms_content_blocks import apply_blocks_to_site_dict, validate_site_content
from tools.export_github import get_github_file, put_github_file
from tools.palette_apply import build_palette_plan, patch_globals_css_content, patch_layout_tsx_content
from tools.vercel_api import trigger_git_deploy, wait_for_deployment_ready

logger = logging.getLogger(__name__)


async def publish_cms_content(project_id: str, *, run_id: str) -> None:
    store = get_managed_projects_store()
    cms = get_cms_content_store()
    project = await store.get_project(project_id)
    if not project or project.deleted_at:
        await store.finish_run(run_id, status="failed", error="Projet introuvable.")
        return
    if not project.github_repo or not project.github_branch:
        await store.finish_run(run_id, status="failed", error="Dépôt GitHub manquant.")
        return

    settings = get_settings()
    blocks_map = await cms.blocks_as_dict(project_id)
    if not blocks_map:
        await store.finish_run(run_id, status="failed", error="Aucun contenu CMS à publier.")
        return

    try:
        patched_files: list[str] = []
        site_path = "content/site.json"
        sha, raw = await get_github_file(
            repo=project.github_repo,
            branch=project.github_branch,
            path=site_path,
            settings=settings,
        )
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("site.json invalide.")
        merged = apply_blocks_to_site_dict(data, blocks_map)
        validated = validate_site_content(merged)
        new_text = json.dumps(validated, ensure_ascii=False, indent=2) + "\n"
        if new_text != raw:
            await put_github_file(
                repo=project.github_repo,
                branch=project.github_branch,
                path=site_path,
                content_utf8=new_text,
                sha=sha,
                message="CyberForge CMS: publish content",
                settings=settings,
            )
            patched_files.append(site_path)

        primary = blocks_map.get("meta.primaryColor", {}).get("value")
        if isinstance(primary, str) and primary.strip().startswith("#"):
            plan = build_palette_plan(
                primary=primary,
                secondary=primary,
                accent=primary,
            )
            for css_path in ("app/globals.css", "src/index.css"):
                try:
                    css_sha, css_raw = await get_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=css_path,
                        settings=settings,
                    )
                except Exception:
                    continue
                new_css = patch_globals_css_content(css_raw, plan)
                if new_css != css_raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=css_path,
                        content_utf8=new_css,
                        sha=css_sha,
                        message=f"CyberForge CMS: palette ({css_path})",
                        settings=settings,
                    )
                    patched_files.append(css_path)
            try:
                layout_sha, layout_raw = await get_github_file(
                    repo=project.github_repo,
                    branch=project.github_branch,
                    path="app/layout.tsx",
                    settings=settings,
                )
                new_layout = patch_layout_tsx_content(layout_raw, plan)
                if new_layout != layout_raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path="app/layout.tsx",
                        content_utf8=new_layout,
                        sha=layout_sha,
                        message="CyberForge CMS: palette (layout.tsx)",
                        settings=settings,
                    )
                    patched_files.append("app/layout.tsx")
            except Exception:
                pass

        if not patched_files:
            await store.finish_run(
                run_id,
                status="succeeded",
                artifacts={"patched_files": [], "note": "Aucune modification détectée"},
            )
            return

        org, repo_name = project.github_repo.split("/", 1)
        triggered = None
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                triggered = await trigger_git_deploy(
                    project_name=project.github_branch,
                    github_org=org,
                    github_repo=repo_name,
                    git_ref=project.github_branch,
                    settings=settings,
                )
                break
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(2.0 + attempt * 2.0)
        if triggered is None:
            raise last_exc or RuntimeError("Déclenchement Vercel impossible.")

        dep = await wait_for_deployment_ready(
            triggered.id, settings=settings, timeout_seconds=300.0
        )
        url_preview = f"https://{dep.url}" if dep.url else None
        url_production = f"https://{project.github_branch}.vercel.app"
        status = "deployed" if dep.ready_state == "READY" else "failed"
        await store.update_project(
            project_id,
            patch={
                "status": status,
                "vercel_deployment_id_last": dep.id,
                "url_preview": url_preview,
                "url_production": url_production if status == "deployed" else url_preview,
                "error_last": None if status == "deployed" else "Échec déploiement Vercel",
            },
        )
        await store.finish_run(
            run_id,
            status="succeeded" if status == "deployed" else "failed",
            error=None if status == "deployed" else "Échec déploiement Vercel",
            artifacts={
                "patched_files": patched_files,
                "vercel_deployment_id": dep.id,
                "cms_publish": True,
            },
        )
    except Exception as exc:
        logger.exception("publish_cms_content failed")
        await store.update_project(
            project_id, patch={"status": "failed", "error_last": str(exc)}
        )
        await store.finish_run(run_id, status="failed", error=str(exc))


async def schedule_cms_publish(project_id: str) -> dict[str, Any]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise ValueError("Supabase non configuré.")
    project = await store.get_project(project_id)
    if not project or project.deleted_at:
        raise ValueError("Projet introuvable.")

    run = await store.create_run(project_id, action="update")
    await store.update_project(project_id, patch={"status": "building", "error_last": None})

    async def _run() -> None:
        await publish_cms_content(project_id, run_id=run.id)

    asyncio.create_task(_run())
    return {
        "scheduled": True,
        "job_id": run.id,
        "run_id": run.id,
        "message": "Publication CMS en cours",
    }
