"""
Routes secrets — coffre local chiffré pour les clés API.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from security.llm_secrets import llm_provider_flags
from security.secret_vault import (
    VaultInvalidPasswordError,
    get_secret_vault,
)

router = APIRouter(tags=["secrets"])


class UnlockRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)


class SaveSecretsRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    google_generative_ai_api_key: str | None = None


class ChangeMasterPasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=256)


@router.get("/secrets/status")
async def secrets_status() -> dict[str, object]:
    vault = get_secret_vault()
    status = vault.status()
    settings = get_settings()
    return {
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": status.configured,
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
    return {
        "ok": True,
        "locked": status.locked,
        "configured": status.configured,
        "effective": llm_provider_flags(settings),
    }


@router.post("/secrets/lock")
async def secrets_lock() -> dict[str, object]:
    vault = get_secret_vault()
    vault.lock()
    return {"ok": True, "locked": True}


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


@router.post("/secrets/save")
async def secrets_save(body: SaveSecretsRequest) -> dict[str, object]:
    vault = get_secret_vault()
    try:
        vault.save(
            body.password,
            secrets={
                "OPENAI_API_KEY": body.openai_api_key,
                "ANTHROPIC_API_KEY": body.anthropic_api_key,
                "DEEPSEEK_API_KEY": body.deepseek_api_key,
                "GOOGLE_GENERATIVE_AI_API_KEY": body.google_generative_ai_api_key,
            },
        )
    except VaultInvalidPasswordError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    status = vault.status()
    settings = get_settings()
    return {
        "ok": True,
        "has_vault": status.has_vault,
        "locked": status.locked,
        "configured": status.configured,
        "effective": llm_provider_flags(settings),
    }

