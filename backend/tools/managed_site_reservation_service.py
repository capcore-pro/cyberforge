"""
Managed site_reservation provisioning.

V1: deploy frontend-only on Vercel; booking API is served by CyberForge backend.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from config import Settings, get_settings
from db.managed_projects_store import ManagedProjectsStore
from tools.export_github import delete_github_branch, push_vitrine_site_to_github
from tools.vercel_api import (
    VercelError,
    delete_project,
    ensure_project_for_github_branch,
    trigger_git_deploy,
    wait_for_deployment_ready,
    delete_deployments_for_branch,
)

logger = logging.getLogger(__name__)


class ManagedSiteReservationError(Exception):
    pass


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _template_files(slug: str) -> dict[str, str]:
    # V1: copy `templates/site-reservation-next` with a minimal substitution.
    try:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        template_dir = root / "templates" / "site-reservation-next"
        if not template_dir.is_dir():
            raise FileNotFoundError(str(template_dir))

        files: dict[str, str] = {}
        for p in template_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(template_dir).as_posix()
            files[rel] = p.read_text(encoding="utf-8")

        # Make package name per slug (optional nice-to-have)
        if "package.json" in files:
            files["package.json"] = files["package.json"].replace(
                "\"name\": \"site-reservation-next\"",
                f"\"name\": \"{slug}-reservation\"",
            )
        return files
    except Exception as exc:
        logger.warning("site-reservation template fallback used: %s", exc)
        # Fallback to inline minimal template (should not happen locally).
        return {"README.md": f"# {slug}\n"}


async def provision_site_reservation(
    *,
    project_id: str,
    run_id: str,
    prompt: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        raise ManagedSiteReservationError("Projet introuvable.")

    slug = project.github_branch
    github_repo = project.github_repo

    await st.update_project(project_id, patch={"status": "building", "error_last": None})

    files = _template_files(slug)
    await push_vitrine_site_to_github(branch_slug=slug, files=files, settings=resolved, repo=github_repo)

    try:
        vercel_project_id = project.vercel_frontend_project_id or project.vercel_project_id
        vercel_project_id = vercel_project_id or await ensure_project_for_github_branch(
            project_name=slug,
            github_repo=github_repo,
            production_branch=slug,
            root_directory=None,
            env={
                "NEXT_PUBLIC_RESERVATION_API_BASE_URL": resolved.demo_api_base_url,
                "NEXT_PUBLIC_RESERVATION_SLUG": slug,
            },
            settings=resolved,
        )
        org, repo_name = github_repo.split("/", 1)
        triggered = await trigger_git_deploy(
            project_name=slug,
            github_org=org,
            github_repo=repo_name,
            git_ref=slug,
            settings=resolved,
        )
        dep = await wait_for_deployment_ready(triggered.id, settings=resolved, timeout_seconds=420.0)
        url_preview = f"https://{dep.url}" if dep.url else None
        url_production = f"https://{slug}.vercel.app"
        status = "deployed" if dep.ready_state == "READY" else "failed"
        await st.update_project(
            project_id,
            patch={
                "title": project.title or slug,
                "prompt_last": prompt,
                "status": status,
                "vercel_project_id": vercel_project_id,
                "vercel_frontend_project_id": vercel_project_id,
                "vercel_deployment_id_last": dep.id,
                "url_preview": url_preview,
                "url_production": url_production if status == "deployed" else url_preview,
                "url_backend": resolved.demo_api_base_url,
                "error_last": None if status == "deployed" else "Vercel deployment failed",
            },
        )
        await st.finish_run(
            run_id,
            status="succeeded" if status == "deployed" else "failed",
            error=None if status == "deployed" else "Vercel deployment failed",
            artifacts={"vercel_project_id": vercel_project_id, "vercel_deployment_id": dep.id},
        )
    except (VercelError, Exception) as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": f"Vercel: {exc}"})
        await st.finish_run(run_id, status="failed", error=str(exc))


async def update_site_reservation(
    *,
    project_id: str,
    prompt: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> None:
    run = await store.create_run(project_id, action="update")
    await provision_site_reservation(
        project_id=project_id,
        run_id=run.id,
        prompt=prompt,
        settings=settings,
        store=store,
    )


async def hard_delete_site_reservation(
    *,
    project_id: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        return
    run = await st.create_run(project_id, action="delete")
    await st.update_project(project_id, patch={"status": "deleting", "error_last": None})

    artifacts: dict[str, Any] = {}
    try:
        pid = project.vercel_frontend_project_id or project.vercel_project_id
        if pid:
            artifacts["vercel_cleanup"] = await delete_deployments_for_branch(
                branch=project.github_branch,
                project_id=pid,
                settings=resolved,
                limit=20,
            )
            artifacts["vercel_project_deleted"] = await delete_project(pid, settings=resolved)
    except Exception as exc:
        artifacts["vercel_error"] = str(exc)

    try:
        artifacts["github_branch_deleted"] = await delete_github_branch(
            repo=project.github_repo,
            branch=project.github_branch,
            settings=resolved,
        )
    except Exception as exc:
        artifacts["github_branch_error"] = str(exc)

    await st.update_project(project_id, patch={"status": "deleted", "deleted_at": _now()})
    await st.finish_run(run.id, status="succeeded", artifacts=artifacts)

