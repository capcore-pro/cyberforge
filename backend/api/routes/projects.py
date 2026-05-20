"""
Routes projets — historique Supabase des générations CoreMindAI.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from db.supabase_store import (
    GenerationRow,
    ProjectDetailResponse,
    ProjectRow,
    SupabaseStoreError,
    get_supabase_store,
)

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
