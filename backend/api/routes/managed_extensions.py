"""
Routes — Extensions navigateur gérées (Manifest V3) + artifact zip.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from config import get_settings
from db.managed_projects_store import ManagedProjectRow, ManagedProjectRunRow, get_managed_projects_store
from tools.managed_extension_service import (
    ManagedExtensionError,
    _extension_files,
    build_extension_zip,
    hard_delete_extension,
    provision_extension,
    update_extension,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extensions"])


class CreateExtensionRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)
    slug: str | None = Field(default=None, max_length=120)


class UpdateExtensionRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=20000)


class CreateExtensionResponse(BaseModel):
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


@router.get("/managed-projects/extensions", response_model=list[ManagedProjectRow])
async def list_extensions() -> list[ManagedProjectRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_projects(type="extension_navigateur")


@router.get("/managed-projects/extensions/{project_id}", response_model=ManagedProjectRow)
async def get_extension(project_id: str) -> ManagedProjectRow:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return row


@router.get("/managed-projects/extensions/{project_id}/runs", response_model=list[ManagedProjectRunRow])
async def list_extension_runs(project_id: str) -> list[ManagedProjectRunRow]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    return await store.list_runs(project_id)


@router.post("/managed-projects/extensions", response_model=CreateExtensionResponse)
async def create_extension(body: CreateExtensionRequest) -> CreateExtensionResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()
    slug = (body.slug or f"ext-{uuid4().hex[:8]}").strip()[:120]
    github_repo = (settings.applications_web_github_repo or "").strip()
    if not github_repo:
        raise HTTPException(status_code=500, detail="APPLICATIONS_WEB_GITHUB_REPO manquant (repo extensions à configurer).")

    project = await store.create_project(
        type="extension_navigateur",
        slug=slug,
        title=None,
        prompt=body.prompt,
        provider="zip",
        github_repo=github_repo,
        github_branch=slug,
        vercel_project_id=None,
    )
    run = await store.create_run(project.id, action="create")

    async def _run() -> None:
        try:
            await provision_extension(
                project_id=project.id,
                run_id=run.id,
                prompt=body.prompt,
                settings=settings,
                store=store,
            )
        except ManagedExtensionError as exc:
            logger.warning("provision_extension failed: %s", exc)

    asyncio.create_task(_run())
    return CreateExtensionResponse(project=project.model_dump(), run=run.model_dump())


@router.post("/managed-projects/extensions/{project_id}/update", response_model=CreateExtensionResponse)
async def update_extension_route(project_id: str, body: UpdateExtensionRequest) -> CreateExtensionResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    settings = get_settings()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    async def _run() -> None:
        await update_extension(project_id=project_id, prompt=body.prompt, settings=settings, store=store)

    asyncio.create_task(_run())
    return CreateExtensionResponse(project={"id": project_id, "status": "scheduled"}, run={"status": "scheduled"})


class DeleteExtensionRequest(BaseModel):
    hard_delete: bool = False


@router.post("/managed-projects/extensions/{project_id}/delete")
async def delete_extension_route(project_id: str, body: DeleteExtensionRequest) -> dict[str, bool]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if body.hard_delete:
        settings = get_settings()

        async def _run() -> None:
            await hard_delete_extension(project_id=project_id, settings=settings, store=store)

        asyncio.create_task(_run())
        return {"deleted": True}

    await store.update_project(
        project_id,
        patch={"status": "deleted", "deleted_at": datetime.now(tz=UTC).isoformat()},
    )
    return {"deleted": True}


@router.get("/managed-projects/extensions/{project_id}/artifact.zip")
async def download_extension_zip(project_id: str) -> Response:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    try:
        files = _extension_files(row.prompt_last, row.github_branch)
        zip_bytes = build_extension_zip(files)
        filename = (row.artifact_filename or f"{row.github_branch}.zip").replace("/", "-")
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("download_extension_zip failed")
        raise HTTPException(status_code=500, detail=str(exc)[:300]) from exc

