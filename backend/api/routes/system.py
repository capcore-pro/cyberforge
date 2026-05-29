"""
Actions système — cache, rechargement configuration.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

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
