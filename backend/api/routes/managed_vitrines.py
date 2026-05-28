"""
Routes V1 — Projets vitrines gérés (CRUD + runs).

Objectif : tout piloter depuis CyberForge (pas d'actions manuelles GitHub/Vercel).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import httpx

from config import get_settings
from db.managed_projects_store import (
    ManagedProjectRow,
    ManagedProjectRunRow,
    get_managed_projects_store,
)
from tools.managed_vitrine_service import ManagedVitrineError, provision_vitrine, update_vitrine
from tools.replicate_screenshot import ReplicateScreenshotClient
from tools.export_github import get_github_file, put_github_file
from tools.vercel_api import trigger_git_deploy, wait_for_deployment_ready
from tools.vitrine_auth_service import (
    VitrineAuthError,
    decrypt_password,
    ensure_auth_row,
    generate_vitrine_password,
    set_auth_settings,
    set_password,
)
from tools.vitrine.content_schema import VitrineSiteContent, UnsplashImage

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


class VitrineAuthResponse(BaseModel):
    enabled: bool
    client_email: str | None = None
    password: str | None = None
    password_updated_at: str | None = None


class UpdateVitrineAuthRequest(BaseModel):
    enabled: bool | None = None
    client_email: str | None = None
    password: str | None = Field(default=None, max_length=200)
    generate_password: bool = False


class UnsplashSearchItem(BaseModel):
    id: str
    url: str
    thumbUrl: str | None = None
    alt: str
    photographer: str | None = None
    photographerUrl: str | None = None
    imageQuery: str | None = None


@router.get("/managed-projects/vitrines/{project_id}/images/search", response_model=list[UnsplashSearchItem])
async def search_unsplash_images(
    project_id: str,
    q: str = Query(..., min_length=2, max_length=120),
    orientation: str | None = Query(default=None),
    page: int = Query(default=1, ge=1, le=50),
) -> list[UnsplashSearchItem]:
    """
    Recherche Unsplash (via API officielle) pour sélectionner une image depuis CyberForge.
    """
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    settings = get_settings()
    access_key = (settings.unsplash_access_key.get_secret_value().strip() if settings.unsplash_access_key else "")
    if not access_key:
        raise HTTPException(status_code=503, detail="UNSPLASH_ACCESS_KEY manquante.")

    params: dict[str, Any] = {"query": q.strip()[:120], "per_page": 12, "page": page}
    if orientation:
        params["orientation"] = orientation
    async with httpx.AsyncClient(timeout=settings.unsplash_http_timeout_seconds) as client:
        r = await client.get(
            "https://api.unsplash.com/search/photos",
            params=params,
            headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Unsplash HTTP {r.status_code}")
        payload = r.json()
        results = payload.get("results") or []
        items: list[UnsplashSearchItem] = []
        for photo in results:
            pid = str(photo.get("id") or "")
            urls = photo.get("urls") or {}
            regular = urls.get("regular") or urls.get("small") or ""
            thumb = urls.get("thumb") or None
            user = photo.get("user") or {}
            photographer = (user.get("name") or "").strip() or None
            links = user.get("links") or {}
            photographer_url = (links.get("html") or "").strip() or None
            alt = (
                photo.get("alt_description")
                or photo.get("description")
                or q
            )
            if pid and regular:
                items.append(
                    UnsplashSearchItem(
                        id=pid,
                        url=str(regular),
                        thumbUrl=str(thumb) if thumb else None,
                        alt=str(alt).strip()[:200] or q,
                        photographer=photographer,
                        photographerUrl=photographer_url,
                        imageQuery=q.strip()[:120],
                    )
                )
        return items


class SetVitrineImageRequest(BaseModel):
    slot: str = Field(..., description="hero | servicesPreview | servicesSection")
    index: int | None = Field(default=None, ge=0, le=20)
    url: str = Field(..., min_length=10, max_length=2000)
    alt: str = Field(..., min_length=3, max_length=200)
    photographer: str | None = Field(default=None, max_length=120)
    photographerUrl: str | None = Field(default=None, max_length=2000)
    imageQuery: str | None = Field(default=None, max_length=120)


@router.post("/managed-projects/vitrines/{project_id}/images/set")
async def set_vitrine_image(project_id: str, body: SetVitrineImageRequest) -> dict[str, Any]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    settings = get_settings()
    run = await store.create_run(project_id, action="update")
    await store.update_project(project_id, patch={"status": "building", "error_last": None})

    async def _run() -> None:
        try:
            sha, raw = await get_github_file(
                repo=project.github_repo,
                branch=project.github_branch,
                path="content/site.json",
                settings=settings,
            )
            content = VitrineSiteContent.model_validate(json.loads(raw))
            image = UnsplashImage(
                url=body.url,
                alt=body.alt,
                photographer=body.photographer,
                photographerUrl=body.photographerUrl,
                imageQuery=body.imageQuery,
            )
            # Patch slot
            if body.slot == "hero":
                content.home.hero.image = image
            elif body.slot == "servicesPreview":
                if body.index is None:
                    raise ValueError("index requis pour servicesPreview")
                content.home.servicesPreview[body.index].image = image
            elif body.slot == "servicesSection":
                if body.index is None:
                    raise ValueError("index requis pour servicesSection")
                content.servicesPage.sections[body.index].image = image
            else:
                raise ValueError("slot invalide")

            new_text = json.dumps(content.model_dump(by_alias=True), ensure_ascii=False, indent=2) + "\n"
            await put_github_file(
                repo=project.github_repo,
                branch=project.github_branch,
                path="content/site.json",
                content_utf8=new_text,
                sha=sha,
                message=f"CyberForge: update vitrine image ({body.slot})",
                settings=settings,
            )

            # Trigger Vercel deploy
            org, repo_name = project.github_repo.split("/", 1)
            last_exc: Exception | None = None
            triggered = None
            for attempt in range(3):
                try:
                    triggered = await trigger_git_deploy(
                        project_name=project.github_branch,
                        github_org=org,
                        github_repo=repo_name,
                        git_ref=project.github_branch,
                        settings=settings,
                    )
                    break
                except Exception as exc:
                    last_exc = exc
                    # GitHub/Vercel can be eventually consistent right after a commit.
                    await asyncio.sleep(2.0 + attempt * 2.0)
            if triggered is None:
                raise last_exc or RuntimeError("Vercel trigger deploy failed")
            dep = await wait_for_deployment_ready(triggered.id, settings=settings, timeout_seconds=300.0)
            url_preview = f"https://{dep.url}" if dep.url else None
            url_production = f"https://{project.github_branch}.vercel.app"
            status = "deployed" if dep.ready_state == "READY" else "failed"
            await store.update_project(
                project_id,
                patch={
                    "status": status,
                    "vercel_deployment_id_last": dep.id,
                    "url_preview": url_preview,
                    "url_production": url_production if status == "deployed" else url_preview,
                    "error_last": None if status == "deployed" else "Vercel deployment failed",
                },
            )
            await store.finish_run(
                run.id,
                status="succeeded" if status == "deployed" else "failed",
                error=None if status == "deployed" else "Vercel deployment failed",
                artifacts={"vercel_deployment_id": dep.id, "slot": body.slot, "index": body.index},
            )
        except Exception as exc:
            logger.exception("set_vitrine_image failed")
            await store.update_project(project_id, patch={"status": "failed", "error_last": str(exc)})
            await store.finish_run(run.id, status="failed", error=str(exc))

    asyncio.create_task(_run())
    return {"scheduled": True, "run_id": run.id}


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


@router.get("/managed-projects/vitrines/{project_id}/preview")
async def get_vitrine_preview(project_id: str) -> dict[str, str | None]:
    """
    Retourne un screenshot (Replicate si configuré) de la vitrine, pour aperçu intégré.
    """
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    url = (row.url_production or row.url_preview or "").strip()
    if not url:
        return {"screenshot_url": None}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"User-Agent": "CyberForge/preview"})
            html = resp.text if resp.status_code < 400 else ""
    except Exception:
        html = ""

    client = ReplicateScreenshotClient(settings=get_settings())
    result = await client.screenshot_html(
        html,
        title=row.title or row.slug,
        width=1280,
        height=720,
    )
    return {"screenshot_url": result.screenshot_url}


@router.get("/managed-projects/vitrines/{project_id}/auth", response_model=VitrineAuthResponse)
async def get_vitrine_auth(project_id: str) -> VitrineAuthResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    auth = await ensure_auth_row(store, project_id)
    return VitrineAuthResponse(
        enabled=bool(auth.enabled),
        client_email=auth.client_email,
        password=decrypt_password(auth),
        password_updated_at=auth.password_updated_at,
    )


@router.post("/managed-projects/vitrines/{project_id}/auth", response_model=VitrineAuthResponse)
async def update_vitrine_auth(project_id: str, body: UpdateVitrineAuthRequest) -> VitrineAuthResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    try:
        auth = await ensure_auth_row(store, project_id)
        if body.enabled is not None or body.client_email is not None:
            auth = await set_auth_settings(
                store=store,
                project_id=project_id,
                enabled=body.enabled,
                client_email=body.client_email,
            )
        if body.generate_password:
            new_pwd = generate_vitrine_password()
            auth = await set_password(store=store, project_id=project_id, password=new_pwd)
        elif body.password is not None and body.password.strip():
            auth = await set_password(store=store, project_id=project_id, password=body.password)
        return VitrineAuthResponse(
            enabled=bool(auth.enabled),
            client_email=auth.client_email,
            password=decrypt_password(auth),
            password_updated_at=auth.password_updated_at,
        )
    except VitrineAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

