"""
Service V1 — gestion complète des vitrines depuis CyberForge.

Créer / Modifier / Supprimer :
- build_vitrine_site (LLM + scaffold)
- push_vitrine_site_to_github (branche = site)
- poll Vercel deployment lié à la branche
"""

from __future__ import annotations

import logging
from typing import Any
from datetime import UTC, datetime

from config import Settings, get_settings, plain_secret_str
from db.managed_projects_store import ManagedProjectsStore, get_managed_projects_store
from tools.export_github import (
    GitHubExportError,
    delete_github_branch,
    push_vitrine_site_to_github,
    vitrine_branch_name,
)
from tools.vercel_api import (
    VercelError,
    delete_deployments_for_branch,
    ensure_project_for_vitrine_branch,
    delete_project as vercel_delete_project,
    resolve_vitrines_project_id,
    trigger_git_deploy,
    wait_for_deployment_ready,
    wait_for_branch_deployment_ready,
)
from tools.vitrine.build import build_vitrine_site

logger = logging.getLogger(__name__)


class ManagedVitrineError(Exception):
    pass


async def provision_vitrine(
    *,
    project_id: str,
    run_id: str,
    prompt: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore | None = None,
) -> None:
    """
    Exécute la chaîne complète pour un projet déjà créé en base :
    build → push GitHub → poll Vercel → update statut.
    """
    resolved = settings or get_settings()
    st = store or get_managed_projects_store()
    project = await st.get_project(project_id)
    if not project:
        raise ManagedVitrineError("Projet introuvable.")

    github_repo = (project.github_repo or "").strip()
    if not github_repo:
        raise ManagedVitrineError("github_repo manquant sur le projet.")
    if not plain_secret_str(resolved.github_token):
        raise ManagedVitrineError("GITHUB_TOKEN manquant.")

    try:
        build = await build_vitrine_site(prompt, settings=resolved)
        files = {f.path: f.content for f in build.generation.files}
        github_url = await push_vitrine_site_to_github(
            branch_slug=project.github_branch,
            files=files,
            settings=resolved,
            repo=github_repo,
        )

        # Clean client URL: one Vercel project per vitrine => https://<slug>.vercel.app
        vitrine_backend_url = (getattr(resolved, "demo_api_base_url", None) or "").strip() or "https://cyberforge-backend-production.up.railway.app"
        vercel_project_id = project.vercel_project_id or await ensure_project_for_vitrine_branch(
            project_name=project.github_branch,
            github_repo=github_repo,
            production_branch=project.github_branch,
            vitrine_backend_url=vitrine_backend_url,
            settings=resolved,
        )
        # Déclenche un deploy Git explicite (évite l'attente de webhooks)
        github_org, github_repo_name = github_repo.split("/", 1)
        triggered = await trigger_git_deploy(
            project_name=project.github_branch,
            github_org=github_org,
            github_repo=github_repo_name,
            git_ref=project.github_branch,
            settings=resolved,
        )
        dep = await wait_for_deployment_ready(triggered.id, settings=resolved, timeout_seconds=300.0)
        url_preview = f"https://{dep.url}" if dep.url else None
        url_production = f"https://{project.github_branch}.vercel.app"
        status = "deployed" if dep.ready_state == "READY" else "failed"

        await st.update_project(
            project_id,
            patch={
                "title": build.content.meta.businessName,
                "prompt_last": prompt,
                "status": status,
                "vercel_project_id": vercel_project_id,
                "vercel_deployment_id_last": dep.id,
                "url_preview": url_preview,
                "url_production": url_production if status == "deployed" else url_preview,
                "error_last": None if status == "deployed" else "Vercel deployment failed",
            },
        )
        await st.finish_run(
            run_id,
            status="succeeded" if status == "deployed" else "failed",
            error=None if status == "deployed" else "Vercel deployment failed",
            artifacts={
                "github_url": github_url,
                "vercel_deployment_id": dep.id,
                "vercel_url_preview": url_preview,
                "vercel_url_production": url_production,
                "vercel_ready_state": dep.ready_state,
            },
        )
    except (GitHubExportError, VercelError, ManagedVitrineError) as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc), "prompt_last": prompt})
        await st.finish_run(run_id, status="failed", error=str(exc), artifacts={})
    except Exception as exc:
        logger.exception("provision_vitrine unexpected failure")
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc), "prompt_last": prompt})
        await st.finish_run(run_id, status="failed", error=str(exc), artifacts={})


async def update_vitrine(
    *,
    project_id: str,
    prompt: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = settings or get_settings()
    st = store or get_managed_projects_store()
    project = await st.get_project(project_id)
    if not project:
        raise ManagedVitrineError("Projet introuvable.")

    run = await st.create_run(project_id, action="update")
    await st.update_project(project_id, patch={"status": "building", "prompt_last": prompt, "error_last": None})

    try:
        build = await build_vitrine_site(prompt, settings=resolved)
        files = {f.path: f.content for f in build.generation.files}
        github_url = await push_vitrine_site_to_github(
            branch_slug=project.github_branch,
            files=files,
            settings=resolved,
            repo=project.github_repo,
        )

        vitrine_backend_url = (getattr(resolved, "demo_api_base_url", None) or "").strip() or "https://cyberforge-backend-production.up.railway.app"
        vercel_project_id = project.vercel_project_id or await ensure_project_for_vitrine_branch(
            project_name=project.github_branch,
            github_repo=project.github_repo,
            production_branch=project.github_branch,
            vitrine_backend_url=vitrine_backend_url,
            settings=resolved,
        )
        github_org, github_repo_name = project.github_repo.split("/", 1)
        triggered = await trigger_git_deploy(
            project_name=project.github_branch,
            github_org=github_org,
            github_repo=github_repo_name,
            git_ref=project.github_branch,
            settings=resolved,
        )
        dep = await wait_for_deployment_ready(triggered.id, settings=resolved, timeout_seconds=300.0)
        url_preview = f"https://{dep.url}" if dep.url else None
        url_production = f"https://{project.github_branch}.vercel.app"
        status = "deployed" if dep.ready_state == "READY" else "failed"
        await st.update_project(
            project_id,
            patch={
                "status": status,
                "vercel_project_id": vercel_project_id,
                "vercel_deployment_id_last": dep.id,
                "url_preview": url_preview,
                "url_production": url_production if status == "deployed" else url_preview,
                "error_last": None if status == "deployed" else "Vercel deployment failed",
            },
        )
        await st.finish_run(
            run.id,
            status="succeeded" if status == "deployed" else "failed",
            error=None if status == "deployed" else "Vercel deployment failed",
            artifacts={
                "github_url": github_url,
                "vercel_deployment_id": dep.id,
                "vercel_url_preview": url_preview,
                "vercel_url_production": url_production,
                "vercel_ready_state": dep.ready_state,
            },
        )
    except (GitHubExportError, VercelError, ManagedVitrineError) as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
        await st.finish_run(run.id, status="failed", error=str(exc), artifacts={})
    except Exception as exc:
        logger.exception("update_vitrine unexpected failure")
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
        await st.finish_run(run.id, status="failed", error=str(exc), artifacts={})

    refreshed = await st.get_project(project_id)
    runs = await st.list_runs(project_id, limit=1)
    return (refreshed.model_dump() if refreshed else project.model_dump(), runs[0].model_dump() if runs else run.model_dump())


async def hard_delete_vitrine(
    *,
    project_id: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore | None = None,
) -> dict[str, Any]:
    """
    V2: suppression complète.
    - supprime les déploiements Vercel liés à la branche
    - supprime la branche GitHub
    - marque le projet deleted
    """
    resolved = settings or get_settings()
    st = store or get_managed_projects_store()
    project = await st.get_project(project_id)
    if not project:
        raise ManagedVitrineError("Projet introuvable.")

    run = await st.create_run(project_id, action="delete")
    await st.update_project(project_id, patch={"status": "deleting", "error_last": None})

    artifacts: dict[str, Any] = {}
    try:
        if project.vercel_project_id:
            artifacts["vercel_cleanup"] = await delete_deployments_for_branch(
                branch=project.github_branch,
                project_id=project.vercel_project_id,
                settings=resolved,
                limit=25,
            )
            artifacts["vercel_project_deleted"] = await vercel_delete_project(
                project.vercel_project_id,
                settings=resolved,
            )

        artifacts["github_branch_deleted"] = await delete_github_branch(
            repo=project.github_repo,
            branch=project.github_branch,
            settings=resolved,
        )

        await st.update_project(
            project_id,
            patch={
                "status": "deleted",
                "deleted_at": datetime.now(tz=UTC).isoformat(),
                "url_preview": None,
                "url_production": None,
                "error_last": None,
            },
        )
        await st.finish_run(run.id, status="succeeded", artifacts=artifacts)
    except (GitHubExportError, VercelError, ManagedVitrineError) as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
        await st.finish_run(run.id, status="failed", error=str(exc), artifacts=artifacts)
    except Exception as exc:
        logger.exception("hard_delete_vitrine unexpected failure")
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
        await st.finish_run(run.id, status="failed", error=str(exc), artifacts=artifacts)

    return {"ok": True}

