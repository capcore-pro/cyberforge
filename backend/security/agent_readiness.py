"""
Prérequis clés pour le statut agents pipeline v2.
Aligné sur la résolution coffre + .env + Settings (comme /api/secrets/status).
"""

from __future__ import annotations

import os

from config import Settings, get_settings, plain_secret_str
from security.llm_secrets import get_effective_llm_key
from security.secret_vault import get_secret_vault


def _env_nonempty(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _vault_nonempty(env_name: str) -> bool:
    return bool((get_secret_vault().peek(env_name) or "").strip())


def _settings_secret_nonempty(settings: Settings, field_name: str) -> bool:
    return bool(plain_secret_str(getattr(settings, field_name, None)))


def anthropic_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(get_effective_llm_key("ANTHROPIC_API_KEY", s))


def deploy_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    pexels = (
        s.pexels_configured
        or _env_nonempty("PEXELS_API_KEY")
        or _vault_nonempty("PEXELS_API_KEY")
    )
    cloudflare = s.cloudflare_configured or (
        _env_nonempty("CLOUDFLARE_ACCOUNT_ID") and _env_nonempty("CLOUDFLARE_API_TOKEN")
    )
    return pexels and cloudflare


def supabase_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return s.supabase_configured


def stripe_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return (
        _env_nonempty("STRIPE_SECRET_KEY")
        or _settings_secret_nonempty(s, "stripe_secret_key")
        or _vault_nonempty("STRIPE_SECRET_KEY")
    )


def replicate_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return (
        _env_nonempty("REPLICATE_API_KEY")
        or _settings_secret_nonempty(s, "replicate_api_key")
        or _vault_nonempty("REPLICATE_API_KEY")
    )


def brevo_ready(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return (
        _env_nonempty("BREVO_API_KEY")
        or _settings_secret_nonempty(s, "brevo_api_key")
        or _vault_nonempty("BREVO_API_KEY")
    )


def agent_is_active(agent_id: str, settings: Settings | None = None) -> bool:
    """Actif si les clés requises sont disponibles (coffre, .env ou Settings)."""
    if agent_id == "electron":
        return True
    if agent_id in ("brief", "generator", "supervisor"):
        return anthropic_ready(settings)
    if agent_id == "deploy":
        return deploy_ready(settings)
    if agent_id in ("database", "auth"):
        return supabase_ready(settings)
    if agent_id == "payment":
        return stripe_ready(settings)
    if agent_id == "email":
        return brevo_ready(settings)
    if agent_id == "media":
        return replicate_ready(settings)
    return False
