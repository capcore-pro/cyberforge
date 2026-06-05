"""
Routes projets — historique Supabase des générations CoreMindAI.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PROJECT_TYPE_LABELS: dict[str, str] = {
    "vitrine_next": "Vitrine Next",
    "ecommerce": "E-commerce",
    "site_reservation": "Réservation",
    "application_web": "Application web",
    "application_desktop": "Application desktop",
    "extension_navigateur": "Extension navigateur",
    "real_app": "Application React",
}
from db.supabase_store import (
    GenerationRow,
    ProjectDetailResponse,
    ProjectRow,
    SupabaseStoreError,
    get_supabase_store,
)
from tools.demo_template_service import heuristic_demo_seed, seed_as_dict
from tools.pipeline_project_deletion import cleanup_pipeline_project_externals

logger = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


def _not_configured_detail(store: Any) -> dict[str, Any]:
    diag = store.connection_diagnostics()
    return {
        "message": (
            "Supabase non configuré. Ajoutez SUPABASE_URL et "
            "SUPABASE_SECRET_KEY dans backend/.env."
        ),
        "operation": "list_projects",
        "diagnostics": diag,
        "hint": "Redémarrez le backend après modification du .env.",
    }


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    upstream = detail.pop("status_code", None)
    if upstream is not None:
        detail["upstream_status_code"] = upstream
    detail["fastapi_route_registered"] = True
    logger.error(
        "Supabase error on %s: %s | detail=%s",
        route,
        exc,
        detail,
    )
    # 502 = erreur amont (Supabase). Ne pas renvoyer 404 HTTP : le client croit
    # que la route FastAPI /api/projects n'existe pas.
    status = 502
    if upstream == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


@router.get("/projects", response_model=list[ProjectRow])
async def list_projects() -> list[ProjectRow]:
    """Liste les projets enregistrés (plus récents en premier)."""
    store = get_supabase_store()
    if not store.is_configured():
        detail = _not_configured_detail(store)
        logger.warning("GET /api/projects — %s | diagnostics=%s", detail["message"], detail["diagnostics"])
        raise HTTPException(status_code=503, detail=detail)

    try:
        projects = await store.list_projects()
        logger.info("GET /api/projects — %s projet(s)", len(projects))
        return projects
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /api/projects") from exc
    except Exception as exc:
        logger.exception("GET /api/projects — erreur inattendue")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erreur inattendue : {exc}",
                "operation": "list_projects",
                "route": "GET /api/projects",
            },
        ) from exc


@router.get("/projects/{project_id}/demo-seed")
async def get_project_demo_seed(project_id: str) -> dict[str, object]:
    """Seed TaskFlow reconstruite depuis le prompt du projet (panneau Personnaliser)."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        detail = await store.get_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"GET /api/projects/{project_id}/demo-seed"
        ) from exc

    if detail is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    pt_key = (detail.project.project_type or "vitrine_next").strip().lower()
    label = PROJECT_TYPE_LABELS.get(pt_key, detail.project.project_type)
    seed = heuristic_demo_seed(detail.project.prompt, project_type_label=label)
    return seed_as_dict(seed)


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str) -> ProjectDetailResponse:
    """Détail d'un projet et de ses générations."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        detail = await store.get_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, f"GET /api/projects/{project_id}") from exc

    if detail is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return detail


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> dict[str, object]:
    """Supprime le projet Supabase, ses générations et les ressources externes liées."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        existing = await store.get_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"DELETE /api/projects/{project_id}"
        ) from exc

    if existing is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    cleanup = await cleanup_pipeline_project_externals(existing)

    try:
        await store.delete_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"DELETE /api/projects/{project_id}"
        ) from exc

    logger.info(
        "DELETE /api/projects/%s — projet Supabase supprimé | cleanup=%s",
        project_id,
        cleanup,
    )
    return {"deleted": True, "cleanup": cleanup}


class UpdateProjectRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    prompt: str | None = Field(default=None, min_length=3, max_length=8000)


class UpdateManagedProjectRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


@router.patch("/projects/{project_id}", response_model=ProjectRow)
async def update_project(project_id: str, body: UpdateProjectRequest) -> ProjectRow:
    """Met à jour le titre et/ou le prompt d'un projet Supabase."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    if body.title is None and body.prompt is None:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")

    try:
        existing = await store.get_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, f"PATCH /api/projects/{project_id}") from exc

    if existing is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    try:
        updated = await store.update_project_metadata(
            project_id,
            title=body.title,
            prompt=body.prompt,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, f"PATCH /api/projects/{project_id}") from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return updated


@router.post("/projects/{project_id}/duplicate", response_model=ProjectDetailResponse)
async def duplicate_project(project_id: str) -> ProjectDetailResponse:
    """Duplique un projet Supabase et sa dernière génération."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        duplicated = await store.duplicate_project(project_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(
            exc, f"POST /api/projects/{project_id}/duplicate"
        ) from exc

    if duplicated is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return duplicated


@router.patch("/managed-projects/{project_id}", response_model=dict)
async def update_managed_project_metadata(
    project_id: str,
    body: UpdateManagedProjectRequest,
) -> dict[str, str]:
    """Met à jour les métadonnées d'un projet géré (ex. titre)."""
    from db.managed_projects_store import get_managed_projects_store

    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(get_supabase_store()))

    if body.title is None:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")

    row = await store.get_project(project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    try:
        updated = await store.update_project(
            project_id,
            patch={
                "title": body.title.strip(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:
        logger.exception("update_managed_project_metadata failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"id": updated.id, "title": updated.title or updated.slug}
