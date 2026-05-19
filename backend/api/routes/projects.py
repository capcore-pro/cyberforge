"""
Routes projets — historique Supabase des générations CoreMindAI.
"""

from fastapi import APIRouter, HTTPException

from db.supabase_store import (
    GenerationRow,
    ProjectDetailResponse,
    ProjectRow,
    SupabaseStoreError,
    get_supabase_store,
)

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectRow])
async def list_projects() -> list[ProjectRow]:
    """Liste les projets enregistrés (plus récents en premier)."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase non configuré. Ajoutez SUPABASE_URL et "
                "SUPABASE_SECRET_KEY dans backend/.env."
            ),
        )
    try:
        return await store.list_projects()
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str) -> ProjectDetailResponse:
    """Détail d'un projet et de ses générations."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        detail = await store.get_project(project_id)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return detail
