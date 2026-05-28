"""
Routes — Projets site_reservation gérés (CRUD + runs).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.managed_projects_store import ManagedProjectRow, ManagedProjectRunRow, get_managed_projects_store
from tools.managed_site_reservation_service import (
    ManagedSiteReservationError,
    hard_delete_site_reservation,
    provision_site_reservation,
    update_site_reservation,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["site_reservation"])


class CreateReservationSiteRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    slug: str | None = Field(default=None, max_length=120)


class UpdateReservationSiteRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)


class CreateReservationSiteResponse(BaseModel):
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


@router.get("/managed-projects/site-reservation", response_model=list[ManagedProjectRow])
async def list_sites_reservation() -> list[ManagedProjectRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_projects(type="site_reservation")


@router.get("/managed-projects/site-reservation/{project_id}", response_model=ManagedProjectRow)
async def get_site_reservation(project_id: str) -> ManagedProjectRow:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return row


@router.get(
    "/managed-projects/site-reservation/{project_id}/runs",
    response_model=list[ManagedProjectRunRow],
)
async def list_site_reservation_runs(project_id: str) -> list[ManagedProjectRunRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_runs(project_id)


@router.post("/managed-projects/site-reservation", response_model=CreateReservationSiteResponse)
async def create_site_reservation(body: CreateReservationSiteRequest) -> CreateReservationSiteResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()
    slug = (body.slug or f"resa-{uuid4().hex[:8]}").strip()[:120]
    github_repo = (settings.applications_web_github_repo or "").strip()
    if not github_repo:
        raise HTTPException(status_code=500, detail="APPLICATIONS_WEB_GITHUB_REPO manquant (repo sites).")

    project = await store.create_project(
        type="site_reservation",
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
        try:
            await provision_site_reservation(
                project_id=project.id,
                run_id=run.id,
                prompt=body.prompt,
                settings=settings,
                store=store,
            )
        except ManagedSiteReservationError as exc:
            logger.warning("site_reservation provision failed: %s", exc)

    asyncio.create_task(_run())
    return CreateReservationSiteResponse(project=project.model_dump(), run=run.model_dump())


@router.post(
    "/managed-projects/site-reservation/{project_id}/update",
    response_model=CreateReservationSiteResponse,
)
async def update_site_reservation_route(
    project_id: str,
    body: UpdateReservationSiteRequest,
) -> CreateReservationSiteResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    async def _run() -> None:
        await update_site_reservation(project_id=project_id, prompt=body.prompt, settings=settings, store=store)

    asyncio.create_task(_run())
    return CreateReservationSiteResponse(
        project={"id": project_id, "status": "scheduled"},
        run={"status": "scheduled", "action": "update"},
    )


class DeleteReservationSiteRequest(BaseModel):
    hard_delete: bool = False


@router.post("/managed-projects/site-reservation/{project_id}/delete")
async def delete_site_reservation_route(project_id: str, body: DeleteReservationSiteRequest) -> dict[str, bool]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    if body.hard_delete:
        settings = get_settings()

        async def _run() -> None:
            await hard_delete_site_reservation(project_id=project_id, settings=settings, store=store)

        asyncio.create_task(_run())
        return {"deleted": True}

    await store.update_project(project_id, patch={"status": "deleted", "deleted_at": datetime.now(tz=UTC).isoformat()})
    return {"deleted": True}

