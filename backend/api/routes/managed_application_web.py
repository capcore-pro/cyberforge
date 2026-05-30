"""
Routes — Projets application_web gérés (CRUD + runs).

Objectif : tout piloter depuis CyberForge (GitHub branches + Railway backend + Vercel frontend).
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
from db.managed_projects_store import (
    ManagedProjectRow,
    ManagedProjectRunRow,
    get_managed_projects_store,
)
from tools.managed_application_web_service import (
    ManagedApplicationWebError,
    hard_delete_application_web,
    provision_application_web,
    update_application_web,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["application_web"])


class CreateAppWebRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    slug: str | None = Field(default=None, max_length=120)


class UpdateAppWebRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)


class CreateAppWebResponse(BaseModel):
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


@router.get("/managed-projects/application-web", response_model=list[ManagedProjectRow])
async def list_application_web() -> list[ManagedProjectRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    try:
        return await store.list_projects(type="application_web")
    except Exception as exc:
        logger.exception("list_application_web failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/managed-projects/application-web/{project_id}", response_model=ManagedProjectRow)
async def get_application_web(project_id: str) -> ManagedProjectRow:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return row


@router.get(
    "/managed-projects/application-web/{project_id}/runs",
    response_model=list[ManagedProjectRunRow],
)
async def list_application_web_runs(project_id: str) -> list[ManagedProjectRunRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_runs(project_id)


@router.post("/managed-projects/application-web", response_model=CreateAppWebResponse)
async def create_application_web(body: CreateAppWebRequest) -> CreateAppWebResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()

    settings = get_settings()
    slug = (body.slug or f"appweb-{uuid4().hex[:8]}").strip()[:120]
    github_repo = (settings.applications_web_github_repo or "").strip()
    if not github_repo:
        raise HTTPException(status_code=500, detail="APPLICATIONS_WEB_GITHUB_REPO manquant.")

    project = await store.create_project(
        type="application_web",
        slug=slug,
        title=None,
        prompt=body.prompt,
        provider="vercel+railway",
        github_repo=github_repo,
        github_branch=slug,
        vercel_project_id=None,
    )
    run = await store.create_run(project.id, action="create")

    async def _run() -> None:
        try:
            await provision_application_web(
                project_id=project.id,
                run_id=run.id,
                prompt=body.prompt,
                settings=settings,
                store=store,
            )
        except ManagedApplicationWebError as exc:
            logger.warning("application_web provision failed: %s", exc)

    asyncio.create_task(_run())
    return CreateAppWebResponse(project=project.model_dump(), run=run.model_dump())


@router.post(
    "/managed-projects/application-web/{project_id}/update",
    response_model=CreateAppWebResponse,
)
async def update_application_web_route(
    project_id: str,
    body: UpdateAppWebRequest,
) -> CreateAppWebResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()

    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    async def _run() -> None:
        await update_application_web(
            project_id=project_id,
            prompt=body.prompt,
            settings=settings,
            store=store,
        )

    asyncio.create_task(_run())
    return CreateAppWebResponse(
        project={"id": project_id, "status": "scheduled"},
        run={"status": "scheduled", "action": "update"},
    )


class DeleteAppWebRequest(BaseModel):
    hard_delete: bool = False


@router.post("/managed-projects/application-web/{project_id}/delete")
async def delete_application_web_route(project_id: str, body: DeleteAppWebRequest) -> dict[str, bool]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    if body.hard_delete:
        settings = get_settings()
        return await hard_delete_application_web(project_id=project_id, settings=settings, store=store)

    await store.update_project(
        project_id,
        patch={"status": "deleted", "deleted_at": datetime.now(tz=UTC).isoformat()},
    )
    return {"deleted": True}

