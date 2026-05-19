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
    status = "ok" if settings.supabase_configured else "degraded"
    return {
        "status": status,
        "app": settings.app_name,
        "version": APP_VERSION,
        "supabase": "configured" if settings.supabase_configured else "missing",
    }
