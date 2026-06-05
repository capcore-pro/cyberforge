"""
Actions système — cache, rechargement configuration, logs récents.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from api.recent_logs import export_all_lines, get_recent_lines
from api.routes.health import APP_VERSION
from config import get_settings, refresh_settings
from security.secret_vault import get_secret_vault

router = APIRouter(tags=["system"])


class SystemInfoResponse(BaseModel):
    version: str
    app_name: str


class ActionResponse(BaseModel):
    ok: bool
    message: str


class SystemLogsResponse(BaseModel):
    lines: list[str]
    backend_port: int


@router.get("/system/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    settings = get_settings()
    return SystemInfoResponse(
        version=APP_VERSION,
        app_name=settings.app_name,
    )


@router.post("/system/clear-cache", response_model=ActionResponse)
async def clear_cache() -> ActionResponse:
    refresh_settings()
    vault = get_secret_vault()
    if not vault.is_locked():
        vault.lock()
    return ActionResponse(
        ok=True,
        message="Cache rechargé et coffre verrouillé. Les paramètres .env ont été relus.",
    )


@router.post("/system/restart-backend", response_model=ActionResponse)
async def restart_backend() -> ActionResponse:
    refresh_settings()
    return ActionResponse(
        ok=True,
        message=(
            "Configuration rechargée. Si le backend tourne en processus séparé, "
            "arrêtez-le puis relancez-le (script de démarrage CyberForge)."
        ),
    )


@router.get("/system/logs", response_model=SystemLogsResponse)
async def system_logs(limit: int = Query(default=5, ge=1, le=50)) -> SystemLogsResponse:
    settings = get_settings()
    return SystemLogsResponse(
        lines=get_recent_lines(limit),
        backend_port=settings.backend_port,
    )


@router.get("/system/logs/export")
async def export_logs() -> PlainTextResponse:
    body = export_all_lines() or "(aucun log enregistré)"
    return PlainTextResponse(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="cyberforge-logs.txt"'},
    )
