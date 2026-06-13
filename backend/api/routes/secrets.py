"""
Routes secrets — coffre local chiffré pour les clés API.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Cherche le .env dans le dossier backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    # Fallback sur le .env à la racine
    load_dotenv(override=True)

# Debug temporaire — à supprimer après
logging.info(f"ANTHROPIC_API_KEY présente: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
logging.info(f".env path: {env_path} — existe: {env_path.exists()}")

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import Settings, get_settings, plain_secret_str, refresh_settings
from security.cloudflare_env import load_cloudflare_from_env
from security.env_file import upsert_env_vars
from security.llm_secrets import llm_provider_flags
from security.secret_vault import (
    VaultInvalidPasswordError,
    get_secret_vault,
)
from tools.api_key_tester import test_api_key

_PROVIDER_ENV: dict[str, tuple[str, str]] = {
    "openai": ("OPENAI_API_KEY", "openai_api_key"),
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic_api_key"),
    "deepseek": ("DEEPSEEK_API_KEY", "deepseek_api_key"),
    "v0": ("V0_API_KEY", "v0_api_key"),
    "replicate": ("REPLICATE_API_KEY", "replicate_api_key"),
    "tavily": ("TAVILY_API_KEY", "tavily_api_key"),
    "railway": ("RAILWAY_API_KEY", "railway_api_key"),
    "vercel": ("VERCEL_TOKEN", "vercel_token"),
    "github": ("GITHUB_TOKEN", "github_token"),
    "brevo": ("BREVO_API_KEY", "brevo_api_key"),
    "stripe": ("STRIPE_SECRET_KEY", "stripe_secret_key"),
    "brave_search": ("BRAVE_SEARCH_API_KEY", "brave_search_api_key"),
    "exa": ("EXA_API_KEY", "exa_api_key"),
}

router = APIRouter(tags=["secrets"])

_VAULT_KEY_PROVIDER: dict[str, str] = {
    env_name: provider for provider, (env_name, _) in _PROVIDER_ENV.items()
}


def _schedule_api_key_changed_event(key_name: str) -> None:
    async def _log() -> None:
        from db.security_store import get_security_store

        await get_security_store().log_event(
            event_type="api_key_changed",
            severity="low",
            source="settings",
            description=f"Clé {key_name} modifiée",
        )

    asyncio.create_task(_log())


def _validate_vault_secrets(
    secrets: dict[str, str | None],
) -> tuple[dict[str, str | None], list[str], list[dict[str, str]]]:
    validated: dict[str, str | None] = {}
    saved_keys: list[str] = []
    warnings: list[dict[str, str]] = []

    for key_name, value in secrets.items():
        if value is None or not str(value).strip():
            validated[key_name] = value
            continue

        provider = _VAULT_KEY_PROVIDER.get(key_name)
        if provider:
            valid, _message = test_api_key(provider, str(value))
            if not valid:
                warnings.append(
                    {
                        "key": key_name,
                        "message": "Clé invalide — vérifiez la valeur",
                    }
                )
                validated[key_name] = None
                continue

        validated[key_name] = value
        saved_keys.append(key_name)

    return validated, saved_keys, warnings


def _env_nonempty(env_name: str) -> bool:
    return bool((os.getenv(env_name) or "").strip())


def _settings_field_nonempty(settings: Settings, field_name: str) -> bool:
    raw = getattr(settings, field_name, None)
    return bool(plain_secret_str(raw))


def _resolve_api_key(provider: str, override: str | None, settings: Settings) -> str | None:
    key = (provider or "").strip().lower()
    if override and override.strip():
        return override.strip()
    mapping = _PROVIDER_ENV.get(key)
    if not mapping:
        return None
    env_name, field_name = mapping
    vault_val = get_secret_vault().peek(env_name)
    if vault_val:
        return vault_val
    env_val = (os.getenv(env_name) or "").strip()
    if env_val:
        return env_val
    if key == "railway":
        railway_token = (os.getenv("RAILWAY_TOKEN") or "").strip()
        if railway_token:
            return railway_token
    raw = getattr(settings, field_name, None)
    text = plain_secret_str(raw)
    return text or None


def _provider_configured(
    provider: str,
    vault_configured: dict[str, bool],
    settings: Settings,
) -> bool:
    if vault_configured.get(provider):
        return True

    if provider == "cloudflare":
        return settings.cloudflare_configured or (
            _env_nonempty("CLOUDFLARE_ACCOUNT_ID")
            and _env_nonempty("CLOUDFLARE_API_TOKEN")
        )
    if provider == "pexels":
        return settings.pexels_configured or _env_nonempty("PEXELS_API_KEY")
    if provider == "firecrawl":
        return settings.firecrawl_configured or _env_nonempty("FIRECRAWL_API_KEY")

    mapping = _PROVIDER_ENV.get(provider)
    if not mapping:
        return bool(vault_configured.get(provider))

    env_name, field_name = mapping
    if _env_nonempty(env_name):
        return True
    if provider == "railway" and _env_nonempty("RAILWAY_TOKEN"):
        return True
    return _settings_field_nonempty(settings, field_name)


def _merge_configured_flags(
    vault_configured: dict[str, bool],
    settings: Settings,
) -> dict[str, bool]:
    providers = set(vault_configured.keys()) | set(_PROVIDER_ENV.keys()) | {
        "cloudflare",
        "pexels",
        "firecrawl",
    }
    return {
        provider: _provider_configured(provider, vault_configured, settings)
        for provider in providers
    }


class UnlockRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)


class SaveSecretsRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    google_generative_ai_api_key: str | None = None
    v0_api_key: str | None = None
    replicate_api_key: str | None = None
    tavily_api_key: str | None = None
    railway_api_key: str | None = None
    vercel_token: str | None = None
    github_token: str | None = None
    brevo_api_key: str | None = None
    stripe_secret_key: str | None = None
    brave_search_api_key: str | None = None
    exa_api_key: str | None = None
    pexels_api_key: str | None = None
    firecrawl_api_key: str | None = None
    cloudflare_account_id: str | None = None
    cloudflare_api_token: str | None = None


class TestSecretRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=32)
    api_key: str | None = Field(default=None, max_length=512)


class TestSecretResponse(BaseModel):
    valid: bool
    message: str


class ChangeMasterPasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=256)


@router.get("/secrets/status")
async def secrets_status() -> dict[str, object]:
    vault = get_secret_vault()
    status = vault.status()
    settings = get_settings()
    configured = _merge_configured_flags(status.configured, settings)
    return {
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": configured,
        "effective": llm_provider_flags(settings),
        "vault_path": str(vault.path),
    }


@router.post("/secrets/unlock")
async def secrets_unlock(body: UnlockRequest) -> dict[str, object]:
    vault = get_secret_vault()
    try:
        vault.unlock(body.password)
    except VaultInvalidPasswordError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    status = vault.status()
    settings = get_settings()
    configured = _merge_configured_flags(status.configured, settings)
    return {
        "ok": True,
        "locked": status.locked,
        "configured": configured,
        "effective": llm_provider_flags(settings),
    }


@router.post("/secrets/lock")
async def secrets_lock() -> dict[str, object]:
    vault = get_secret_vault()
    vault.lock()
    return {"ok": True, "locked": True}


@router.post("/secrets/reset")
async def secrets_reset() -> dict[str, object]:
    """Supprime le fichier coffre chiffré et remet l'état à zéro."""
    vault = get_secret_vault()
    vault.reset()
    status = vault.status()
    settings = get_settings()
    configured = _merge_configured_flags(status.configured, settings)
    return {
        "ok": True,
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": configured,
        "effective": llm_provider_flags(settings),
        "vault_path": str(vault.path),
    }


@router.post("/secrets/change-password")
async def secrets_change_password(body: ChangeMasterPasswordRequest) -> dict[str, object]:
    vault = get_secret_vault()
    try:
        vault.change_master_password(body.old_password, body.new_password)
    except VaultInvalidPasswordError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    status = vault.status()
    settings = get_settings()
    return {
        "ok": True,
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": status.configured,
        "effective": llm_provider_flags(settings),
    }


@router.post("/secrets/test", response_model=TestSecretResponse)
async def secrets_test(body: TestSecretRequest) -> TestSecretResponse:
    settings = get_settings()
    token = _resolve_api_key(body.provider, body.api_key, settings)
    if not token:
        return TestSecretResponse(valid=False, message="Clé manquante")
    valid, message = test_api_key(body.provider, token)
    return TestSecretResponse(valid=valid, message=message)


@router.post("/secrets/save")
async def secrets_save(body: SaveSecretsRequest) -> dict[str, object]:
    vault = get_secret_vault()
    raw_secrets = {
        "OPENAI_API_KEY": body.openai_api_key,
        "ANTHROPIC_API_KEY": body.anthropic_api_key,
        "DEEPSEEK_API_KEY": body.deepseek_api_key,
        "GOOGLE_GENERATIVE_AI_API_KEY": body.google_generative_ai_api_key,
        "V0_API_KEY": body.v0_api_key,
        "REPLICATE_API_KEY": body.replicate_api_key,
        "TAVILY_API_KEY": body.tavily_api_key,
        "RAILWAY_API_KEY": body.railway_api_key,
        "VERCEL_TOKEN": body.vercel_token,
        "GITHUB_TOKEN": body.github_token,
        "BREVO_API_KEY": body.brevo_api_key,
        "STRIPE_SECRET_KEY": body.stripe_secret_key,
        "BRAVE_SEARCH_API_KEY": body.brave_search_api_key,
        "EXA_API_KEY": body.exa_api_key,
    }
    secrets, saved_keys, warnings = _validate_vault_secrets(raw_secrets)

    try:
        vault.save(body.password, secrets=secrets)
    except VaultInvalidPasswordError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    for key_name in saved_keys:
        _schedule_api_key_changed_event(key_name)

    env_updates: dict[str, str | None] = {}
    if secrets.get("BREVO_API_KEY") and str(secrets["BREVO_API_KEY"]).strip():
        env_updates["BREVO_API_KEY"] = str(secrets["BREVO_API_KEY"]).strip()
    if secrets.get("STRIPE_SECRET_KEY") and str(secrets["STRIPE_SECRET_KEY"]).strip():
        env_updates["STRIPE_SECRET_KEY"] = str(secrets["STRIPE_SECRET_KEY"]).strip()
    if body.pexels_api_key and body.pexels_api_key.strip():
        env_updates["PEXELS_API_KEY"] = body.pexels_api_key.strip()
    if body.firecrawl_api_key and body.firecrawl_api_key.strip():
        env_updates["FIRECRAWL_API_KEY"] = body.firecrawl_api_key.strip()
    if body.cloudflare_account_id and body.cloudflare_account_id.strip():
        env_updates["CLOUDFLARE_ACCOUNT_ID"] = body.cloudflare_account_id.strip()
    if body.cloudflare_api_token and body.cloudflare_api_token.strip():
        env_updates["CLOUDFLARE_API_TOKEN"] = body.cloudflare_api_token.strip()
    if env_updates:
        upsert_env_vars(env_updates)
        refresh_settings()
        load_cloudflare_from_env()

    status = vault.status()
    settings = get_settings()
    configured = _merge_configured_flags(status.configured, settings)
    return {
        "ok": True,
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": configured,
        "effective": llm_provider_flags(settings),
        "saved": saved_keys,
        "warnings": warnings,
    }

