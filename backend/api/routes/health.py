"""
Route de santé — permet au frontend de vérifier la disponibilité du backend.
"""

from fastapi import APIRouter

from config import get_settings
from security.cloudflare_env import cloudflare_configured
from security.llm_secrets import any_llm_key_configured, llm_provider_flags
from security.secret_vault import get_secret_vault

router = APIRouter(tags=["health"])

APP_VERSION = "0.8.0"


@router.get("/health")
async def health_check() -> dict[str, str | bool | dict[str, bool]]:
    """
    Point de contrôle minimal.
    Ne renvoie jamais de secrets ni de clés API.
    """
    settings = get_settings()
    vault = get_secret_vault()
    vault_status = vault.status()
    llm_ready = any_llm_key_configured(settings)
    status = "ok" if settings.supabase_configured and llm_ready else "degraded"
    return {
        "status": status,
        "environment": settings.environment,
        "app": settings.app_name,
        "version": APP_VERSION,
        "supabase": "configured" if settings.supabase_configured else "missing",
        "secrets_vault": {
            "has_vault": vault_status.has_vault,
            "locked": vault_status.locked,
        },
        "llm_configured": llm_provider_flags(settings),
        "cloudflare_configured": cloudflare_configured(),
    }
