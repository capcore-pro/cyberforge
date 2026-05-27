"""
Routes V1 — Projets vitrines gérés (CRUD + runs).

Objectif : tout piloter depuis CyberForge (pas d'actions manuelles GitHub/Vercel).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.managed_projects_store import (
    ManagedProjectRow,
    ManagedProjectRunRow,
    get_managed_projects_store,
)
from tools.managed_vitrine_service import ManagedVitrineError, provision_vitrine, update_vitrine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vitrines"])


class CreateVitrineRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    slug: str | None = Field(default=None, max_length=120)


class UpdateVitrineRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)


class CreateVitrineResponse(BaseModel):
    project: dict[str, Any]
    run: dict[str, Any]


def _not_configured() -> HTTPException:
    store = get_managed_projects_store()
    return HTTPException(
        status_code=503,
        detail={
            "message": "Supabase non configuré (SUPABASE_URL + SUPABASE_SECRET_KEY requis).",
            "diagnostics": store.connection_diagnostics(),
        },
    )


@router.get("/managed-projects/vitrines", response_model=list[ManagedProjectRow])
async def list_vitrines() -> list[ManagedProjectRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    try:
        return await store.list_projects(type="vitrine_next")
    except Exception as exc:
        logger.exception("list_vitrines failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/managed-projects/vitrines/{project_id}", response_model=ManagedProjectRow)
async def get_vitrine(project_id: str) -> ManagedProjectRow:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return row


@router.get(
    "/managed-projects/vitrines/{project_id}/runs",
    response_model=list[ManagedProjectRunRow],
)
async def list_vitrine_runs(project_id: str) -> list[ManagedProjectRunRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_runs(project_id)


@router.post("/managed-projects/vitrines", response_model=CreateVitrineResponse)
async def create_vitrine_project(body: CreateVitrineRequest) -> CreateVitrineResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()

    # Runner async : on renvoie immédiatement, UI poll le projet/runs.
    settings = get_settings()
    slug = (body.slug or f"vitrine-{uuid4().hex[:8]}").strip()[:120]
    github_repo = (settings.vitrines_github_repo or "").strip()
    if not github_repo:
        raise HTTPException(status_code=500, detail="VITRINES_GITHUB_REPO manquant.")

    project = await store.create_project(
        type="vitrine_next",
        slug=slug,
        title=None,
        prompt=body.prompt,
        provider="vercel",
        github_repo=github_repo,
        github_branch=slug,
        vercel_project_id=None,
    )
    run = await store.create_run(project.id, action="create")

    async def _run() -> None:
        await provision_vitrine(
            project_id=project.id,
            run_id=run.id,
            prompt=body.prompt,
            settings=settings,
            store=store,
        )

    asyncio.create_task(_run())

    return CreateVitrineResponse(project=project.model_dump(), run=run.model_dump())


@router.post(
    "/managed-projects/vitrines/{project_id}/update",
    response_model=CreateVitrineResponse,
)
async def update_vitrine_project(project_id: str, body: UpdateVitrineRequest) -> CreateVitrineResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()

    # validate exists
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    async def _run() -> None:
        await update_vitrine(project_id=project_id, prompt=body.prompt, settings=settings, store=store)

    asyncio.create_task(_run())
    return CreateVitrineResponse(
        project={"id": project_id, "status": "scheduled"},
        run={"status": "scheduled", "action": "update"},
    )


class DeleteVitrineRequest(BaseModel):
    hard_delete: bool = False


@router.post("/managed-projects/vitrines/{project_id}/delete")
async def delete_vitrine_project(project_id: str, body: DeleteVitrineRequest) -> dict[str, bool]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    if body.hard_delete:
        from tools.managed_vitrine_service import hard_delete_vitrine

        settings = get_settings()

        async def _run() -> None:
            await hard_delete_vitrine(project_id=project_id, settings=settings, store=store)

        asyncio.create_task(_run())
        return {"deleted": True}

    # V1 behavior: soft delete
    await store.update_project(
        project_id,
        patch={"status": "deleted", "deleted_at": datetime.now(tz=UTC).isoformat()},
    )
    return {"deleted": True}

