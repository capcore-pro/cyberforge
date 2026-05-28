"""
Public endpoints for vitrines (called from Vercel-hosted Next.js sites).

These endpoints do NOT require CyberForge auth (V1), so they must only expose
safe operations:
- check whether password protection is enabled
- unlock (verify password)
- change password (requires current password)
- forgot password (email new password to the registered client email)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.managed_projects_store import get_managed_projects_store
from tools.capcore_notify import _send_brevo_email  # reuse Brevo transport
from tools.vitrine_auth_service import (
    VitrineAuthError,
    decrypt_password,
    email_matches,
    ensure_auth_row,
    generate_vitrine_password,
    set_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vitrine-auth"])


class VitrineAuthStatusResponse(BaseModel):
    enabled: bool


class UnlockRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)


class UnlockResponse(BaseModel):
    ok: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=250)


async def _get_project_id_by_slug(slug: str) -> str:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    project_id = await store.get_project_id_by_slug(slug=slug, type="vitrine_next")
    if not project_id:
        raise HTTPException(status_code=404, detail="Vitrine introuvable.")
    return project_id


@router.get("/vitrines/{slug}/auth/status", response_model=VitrineAuthStatusResponse)
async def vitrine_auth_status(slug: str) -> VitrineAuthStatusResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    project_id = await _get_project_id_by_slug(slug)
    auth = await ensure_auth_row(store, project_id)
    return VitrineAuthStatusResponse(enabled=bool(auth.enabled))


@router.post("/vitrines/{slug}/auth/unlock", response_model=UnlockResponse)
async def vitrine_unlock(slug: str, body: UnlockRequest) -> UnlockResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    project_id = await _get_project_id_by_slug(slug)
    auth = await ensure_auth_row(store, project_id)
    if not auth.enabled:
        return UnlockResponse(ok=True)
    expected = decrypt_password(auth) or ""
    ok = body.password.strip() == expected
    return UnlockResponse(ok=ok)


@router.post("/vitrines/{slug}/auth/change-password", response_model=UnlockResponse)
async def vitrine_change_password(slug: str, body: ChangePasswordRequest) -> UnlockResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    project_id = await _get_project_id_by_slug(slug)
    auth = await ensure_auth_row(store, project_id)
    if not auth.enabled:
        raise HTTPException(status_code=403, detail="Protection mot de passe désactivée.")
    expected = decrypt_password(auth) or ""
    if body.current_password.strip() != expected:
        return UnlockResponse(ok=False)
    try:
        await set_password(store=store, project_id=project_id, password=body.new_password)
    except VitrineAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UnlockResponse(ok=True)


@router.post("/vitrines/{slug}/auth/forgot-password", response_model=UnlockResponse)
async def vitrine_forgot_password(slug: str, body: ForgotPasswordRequest) -> UnlockResponse:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    settings = get_settings()

    project_id = await _get_project_id_by_slug(slug)
    auth = await ensure_auth_row(store, project_id)
    if not auth.enabled:
        raise HTTPException(status_code=403, detail="Protection mot de passe désactivée.")
    if not email_matches(auth, body.email):
        # Do not leak existence; respond ok=false.
        return UnlockResponse(ok=False)

    new_pwd = generate_vitrine_password()
    await set_password(store=store, project_id=project_id, password=new_pwd)

    subject = f"Nouveau mot de passe — vitrine {slug}"
    msg = "\n".join(
        [
            f"Bonjour,",
            "",
            f"Voici votre nouveau mot de passe pour la vitrine {slug}:",
            "",
            new_pwd,
            "",
            "Vous pourrez le modifier depuis la page de changement de mot de passe.",
        ]
    )
    try:
        await _send_brevo_email(to_email=body.email.strip(), subject=subject, body=msg)
    except Exception as exc:
        logger.warning("Brevo send failed: %s", exc)
        raise HTTPException(status_code=502, detail="Envoi email impossible.") from exc

    return UnlockResponse(ok=True)

