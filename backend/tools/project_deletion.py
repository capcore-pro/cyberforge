"""
Suppression complète d'un projet géré — Vercel, GitHub, Railway, Supabase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from config import Settings, get_settings, plain_secret_str
from db.managed_projects_store import ManagedProjectRow, ManagedProjectsStore, get_managed_projects_store
from db.supabase_store import SupabaseStore, get_supabase_store
from tools.export_github import GitHubExportError, delete_github_branch
from tools.export_railway import delete_railway_service
from tools.vercel_api import VercelError, delete_deployments_for_branch, delete_project as vercel_delete_project

logger = logging.getLogger(__name__)

ReportStatus = Literal["ok", "skipped", "error"]


@dataclass
class DeletionReportItem:
    label: str
    status: ReportStatus
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "status": self.status, "detail": self.detail}


@dataclass
class DeletionReport:
    items: list[DeletionReportItem] = field(default_factory=list)

    def ok(self, label: str, detail: str | None = None) -> None:
        self.items.append(DeletionReportItem(label, "ok", detail))

    def skip(self, label: str, detail: str | None = None) -> None:
        self.items.append(DeletionReportItem(label, "skipped", detail))

    def err(self, label: str, detail: str | None = None) -> None:
        self.items.append(DeletionReportItem(label, "error", detail or "Erreur inconnue"))

    @property
    def has_errors(self) -> bool:
        return any(i.status == "error" for i in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deleted": True,
            "ok": not self.has_errors,
            "items": [i.to_dict() for i in self.items],
        }


async def _cleanup_vercel_ids(
    *,
    project: ManagedProjectRow,
    settings: Settings,
    report: DeletionReport,
) -> None:
    ids: list[str] = []
    for raw in (project.vercel_frontend_project_id, project.vercel_project_id):
        cleaned = (raw or "").strip()
        if cleaned and cleaned not in ids:
            ids.append(cleaned)

    if not ids:
        report.skip("Vercel", "Aucun projet Vercel lié")
        return

    for pid in ids:
        try:
            await delete_deployments_for_branch(
                branch=project.github_branch,
                project_id=pid,
                settings=settings,
                limit=25,
            )
            await vercel_delete_project(pid, settings=settings)
            report.ok("Vercel", f"Projet {pid} supprimé")
        except (VercelError, Exception) as exc:
            logger.warning("Vercel delete failed for %s: %s", pid, exc)
            report.err("Vercel", f"{pid} — {exc}")


async def _cleanup_github(
    *,
    project: ManagedProjectRow,
    settings: Settings,
    report: DeletionReport,
) -> None:
    repo = (project.github_repo or "").strip()
    branch = (project.github_branch or "").strip()
    if not repo or not branch:
        report.skip("GitHub", "Repo ou branche manquant")
        return
    try:
        deleted = await delete_github_branch(repo=repo, branch=branch, settings=settings)
        if deleted:
            report.ok("GitHub", f"Branche {branch} supprimée")
        else:
            report.skip("GitHub", f"Branche {branch} introuvable")
    except (GitHubExportError, Exception) as exc:
        logger.warning("GitHub branch delete failed: %s", exc)
        report.err("GitHub", str(exc))


async def _cleanup_railway(
    *,
    project: ManagedProjectRow,
    settings: Settings,
    report: DeletionReport,
) -> None:
    service_id = (project.railway_service_id or "").strip()
    if not service_id:
        report.skip("Railway", "Aucun service lié")
        return
    api_token = plain_secret_str(getattr(settings, "railway_api_key", None))
    if not api_token:
        report.err("Railway", "RAILWAY_API_KEY manquant")
        return
    try:
        deleted = await delete_railway_service(service_id=service_id, token=api_token)
        if deleted:
            report.ok("Railway", f"Service {service_id} supprimé")
        else:
            report.skip("Railway", "Service déjà absent")
    except Exception as exc:
        logger.warning("Railway delete failed: %s", exc)
        report.err("Railway", str(exc))


def _cleanup_extension_zip(project: ManagedProjectRow, report: DeletionReport) -> None:
    slug = (project.github_branch or project.slug or "").strip()
    if not slug:
        report.skip("ZIP local", "Slug manquant")
        return
    backend_root = Path(__file__).resolve().parent.parent
    candidates = [
        backend_root / "data" / "extensions" / f"{slug}.zip",
        backend_root / "exports" / "extensions" / f"{slug}.zip",
    ]
    removed = False
    for path in candidates:
        if path.is_file():
            try:
                path.unlink()
                removed = True
            except OSError as exc:
                report.err("ZIP local", f"{path.name} — {exc}")
                return
    if removed:
        report.ok("ZIP local", f"{slug}.zip supprimé")
    else:
        report.skip("ZIP local", "Aucun fichier local (ZIP généré à la volée)")


async def hard_delete_managed_project(
    *,
    project_id: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore | None = None,
    supabase: SupabaseStore | None = None,
    include_railway: bool = False,
    include_ecommerce: bool = False,
    include_reservation: bool = False,
    include_extension_zip: bool = False,
    include_pipeline_projects: bool = True,
) -> dict[str, Any]:
    """
    Suppression complète : infra externe + données Supabase liées + ligne managed_projects.
    """
    resolved = settings or get_settings()
    st = store or get_managed_projects_store()
    sb = supabase or get_supabase_store()
    report = DeletionReport()

    project = await st.get_project(project_id)
    if not project:
        report.err("Projet", "Introuvable en base")
        return report.to_dict()

    run = await st.create_run(project_id, action="delete")
    await st.update_project(project_id, patch={"status": "deleting", "error_last": None})

    await _cleanup_vercel_ids(project=project, settings=resolved, report=report)
    await _cleanup_github(project=project, settings=resolved, report=report)

    if include_railway:
        await _cleanup_railway(project=project, settings=resolved, report=report)

    if include_extension_zip:
        _cleanup_extension_zip(project, report)

    try:
        if include_ecommerce:
            await st.purge_ecommerce_data(project_id)
            report.ok("Données e-commerce", "Tables nettoyées")
    except Exception as exc:
        logger.warning("ecommerce purge failed: %s", exc)
        report.err("Données e-commerce", str(exc))

    try:
        if include_reservation:
            await st.purge_reservation_data(project_id)
            report.ok("Données réservation", "Tables nettoyées")
    except Exception as exc:
        logger.warning("reservation purge failed: %s", exc)
        report.err("Données réservation", str(exc))

    try:
        auth = await st.get_project_auth(project_id)
        if auth:
            await st.delete_project_auth(project_id)
            report.ok("Mot de passe vitrine", "Auth supprimée")
        else:
            report.skip("Mot de passe vitrine", "Non configuré")
    except Exception as exc:
        logger.warning("auth delete failed: %s", exc)
        report.err("Mot de passe vitrine", str(exc))

    if include_pipeline_projects and sb.is_configured():
        try:
            count = await st.delete_pipeline_projects_by_slug(
                sb,
                slug=project.slug,
                title=project.title,
            )
            if count:
                report.ok("Pipeline Supabase", f"{count} projet(s) + générations supprimés")
            else:
                report.skip("Pipeline Supabase", "Aucune entrée projects correspondante")
        except Exception as exc:
            logger.warning("pipeline projects delete failed: %s", exc)
            report.err("Pipeline Supabase", str(exc))
    else:
        report.skip("Pipeline Supabase", "Non applicable ou Supabase indisponible")

    try:
        await st.purge_managed_project_row(project_id)
        report.ok("Supabase", "managed_projects et runs supprimés")
    except Exception as exc:
        logger.exception("managed project purge failed")
        report.err("Supabase", str(exc))
        await st.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
        await st.finish_run(run.id, status="failed", error=str(exc), artifacts=report.to_dict())
        return report.to_dict()

    await st.finish_run(
        run.id,
        status="failed" if report.has_errors else "succeeded",
        error="Suppression partielle" if report.has_errors else None,
        artifacts=report.to_dict(),
    )
    return report.to_dict()
