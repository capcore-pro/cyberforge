"""
Route de santé — permet au frontend de vérifier la disponibilité du backend.
"""

from fastapi import APIRouter

from config import get_settings

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Point de contrôle minimal.
    Ne renvoie jamais de secrets ni de clés API.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
    }
