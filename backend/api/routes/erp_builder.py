"""
Routes API — ERP Builder (Odoo / ERPNext / Custom + Docker).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.erp_ai import ALL_MODULES, build_recommendation, recommendation_to_dict
from db.erp_store import get_erp_store
from db.supabase_store import SupabaseStoreError
from tools.erp_docker import (
    ErpDockerError,
    generate_compose_for_project,
    get_erp_status,
    restart_erp,
    stop_erp,
    stream_install_logs,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["erp_builder"])


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


ErpType = Literal["odoo", "erpnext", "custom"]
CompanySize = Literal["solo", "small", "medium", "large"]
Budget = Literal["low", "medium", "high"]


class ErpProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    client_name: str = Field(default="", max_length=120)
    company_size: CompanySize = "small"
    budget: Budget = "medium"
    modules: list[str] = Field(default_factory=list)
    erp_type: ErpType | None = None
    primary_color: str = Field(default="#0f1117", pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = None
    domain: str | None = None
    admin_email: str = Field(default="admin@cyberforge.local")
    admin_password: str = Field(default="CyberForge2026!", min_length=8)
    port: int | None = Field(default=None, ge=1024, le=65535)


class ErpProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    client_name: str | None = Field(default=None, max_length=120)
    company_size: CompanySize | None = None
    budget: Budget | None = None
    modules: list[str] | None = None
    erp_type: ErpType | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = None
    domain: str | None = None
    admin_email: str | None = None
    admin_password: str | None = Field(default=None, min_length=8)
    port: int | None = Field(default=None, ge=1024, le=65535)
    status: str | None = None


def _validate_modules(modules: list[str]) -> list[str]:
    return [m for m in modules if m in ALL_MODULES]


def _row_to_project(row: dict[str, Any], *, include_secrets: bool = True) -> dict[str, Any]:
    modules = row.get("modules")
    if not isinstance(modules, list):
        modules = []
    out: dict[str, Any] = {
        "id": str(row.get("id") or ""),
        "name": str(row.get("name") or ""),
        "client_name": row.get("client_name"),
        "erp_type": row.get("erp_type"),
        "company_size": row.get("company_size"),
        "budget": row.get("budget"),
        "modules": modules,
        "primary_color": row.get("primary_color"),
        "logo_url": row.get("logo_url"),
        "domain": row.get("domain"),
        "admin_email": row.get("admin_email"),
        "container_name": row.get("container_name"),
        "port": row.get("port"),
        "status": row.get("status") or "draft",
        "url": row.get("url"),
        "install_logs": row.get("install_logs"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
    if include_secrets:
        out["admin_password"] = row.get("admin_password")
    return out


@router.post("/erp/projects")
async def create_erp_project(body: ErpProjectCreate) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    modules = _validate_modules(body.modules)
    try:
        row = await store.create_project(
            {
                "name": body.name.strip(),
                "client_name": body.client_name.strip(),
                "company_size": body.company_size,
                "budget": body.budget,
                "modules": modules,
                "erp_type": body.erp_type,
                "primary_color": body.primary_color,
                "logo_url": body.logo_url,
                "domain": body.domain,
                "admin_email": body.admin_email,
                "admin_password": body.admin_password,
                "port": body.port,
                "status": "draft",
            }
        )
        return _row_to_project(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/erp/projects")
async def list_erp_projects() -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        rows = await store.list_projects()
        items = [_row_to_project(r) for r in rows]
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/erp/projects/{project_id}")
async def get_erp_project(project_id: str) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_project(project_id)
        if not row:
            raise HTTPException(status_code=404, detail="Projet introuvable.")
        return _row_to_project(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/erp/projects/{project_id}")
async def update_erp_project(project_id: str, body: ErpProjectUpdate) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    patch = body.model_dump(exclude_unset=True)
    if "modules" in patch and patch["modules"] is not None:
        patch["modules"] = _validate_modules(patch["modules"])
    try:
        updated = await store.update_project(project_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail="Projet introuvable.")
        return _row_to_project(updated)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/erp/projects/{project_id}")
async def delete_erp_project(project_id: str) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        try:
            await stop_erp(project_id)
        except ErpDockerError:
            pass
        ok = await store.delete_project(project_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Projet introuvable.")
        return {"deleted": True, "id": project_id}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/erp/projects/{project_id}/recommend")
async def recommend_erp(project_id: str, request: Request) -> StreamingResponse:
    """Recommandation ERP en SSE."""
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _sse_event("agent_start", {"message": "Analyse de votre profil..."})
            if await request.is_disconnected():
                return
            rec = build_recommendation(row)
            yield _sse_event(
                "agent_done",
                {"message": "Recommandation prête", "recommendation": recommendation_to_dict(rec)},
            )
            await store.update_project(
                project_id,
                {
                    "erp_type": rec.erp_type,
                    "modules": rec.modules,
                    "status": "configuring",
                },
            )
            yield _sse_event("done", recommendation_to_dict(rec))
        except Exception as exc:
            logger.exception("ERP recommend failed for %s", project_id)
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/erp/projects/{project_id}/install")
async def install_erp(project_id: str, request: Request) -> StreamingResponse:
    """Installation Docker en SSE."""
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if not row.get("erp_type"):
        raise HTTPException(status_code=400, detail="Choisissez d'abord un type d'ERP.")

    compose, port, container = generate_compose_for_project(row)
    project = {**row, "port": row.get("port") or port}

    async def event_generator() -> AsyncIterator[str]:
        await store.update_project(
            project_id,
            {
                "status": "installing",
                "docker_compose_content": compose,
                "container_name": container,
                "port": port,
                "install_logs": "Installation démarrée...",
            },
        )
        try:
            async for item in stream_install_logs(project_id, compose, project):
                if await request.is_disconnected():
                    return
                ev = item.get("event", "step")
                if ev == "done":
                    yield _sse_event("done", {
                        "url": item.get("url"),
                        "admin_email": item.get("admin_email"),
                        "admin_password": item.get("admin_password"),
                    })
                    await store.update_project(
                        project_id,
                        {
                            "status": "running",
                            "url": item.get("url"),
                            "install_logs": str(item.get("logs") or "")[-8000:],
                        },
                    )
                elif ev == "error":
                    yield _sse_event("error", {"message": item.get("message")})
                    await store.update_project(
                        project_id,
                        {
                            "status": "error",
                            "install_logs": str(item.get("message")),
                        },
                    )
                else:
                    yield _sse_event(ev, {"message": item.get("message", "")})
        except Exception as exc:
            logger.exception("ERP install failed for %s", project_id)
            yield _sse_event("error", {"message": str(exc)})
            await store.update_project(
                project_id, {"status": "error", "install_logs": str(exc)}
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/erp/projects/{project_id}/status")
async def erp_project_status(project_id: str) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    docker_status = await get_erp_status(project_id, row)
    if docker_status.get("running") and row.get("status") != "running":
        await store.update_project(project_id, {"status": "running"})
        row = await store.get_project(project_id) or row
    elif not docker_status.get("running") and row.get("status") == "running":
        await store.update_project(project_id, {"status": "stopped"})
        row = await store.get_project(project_id) or row
    return {
        "project": _row_to_project(row),
        "docker": docker_status,
    }


@router.post("/erp/projects/{project_id}/stop")
async def stop_erp_project(project_id: str) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    try:
        await stop_erp(project_id)
        await store.update_project(project_id, {"status": "stopped"})
        return {"stopped": True, "id": project_id}
    except ErpDockerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/erp/projects/{project_id}/restart")
async def restart_erp_project(project_id: str) -> dict[str, Any]:
    store = get_erp_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_project(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    try:
        result = await restart_erp(project_id, row)
        await store.update_project(project_id, {"status": "running"})
        return {"restarted": True, "id": project_id, "docker": result}
    except ErpDockerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
