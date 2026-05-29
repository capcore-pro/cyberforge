"""
Paramètres profil CapCore — lecture / écriture .env.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import get_settings, refresh_settings
from security.env_file import read_env_value, upsert_env_vars

router = APIRouter(tags=["settings"])


class ProfileResponse(BaseModel):
    email: str
    siret: str
    kbis_media_id: str | None = None


class ProfileUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    siret: str | None = Field(default=None, max_length=20)
    kbis_media_id: str | None = Field(default=None, max_length=64)


@router.get("/settings/profile", response_model=ProfileResponse)
async def get_profile() -> ProfileResponse:
    settings = get_settings()
    kbis_id = read_env_value("MAT_KBIS_MEDIA_ID")
    return ProfileResponse(
        email=(settings.mat_legal_email or settings.capcore_notify_email or "").strip(),
        siret=(settings.mat_siret or "").strip(),
        kbis_media_id=kbis_id,
    )


@router.patch("/settings/profile", response_model=ProfileResponse)
async def update_profile(body: ProfileUpdateRequest) -> ProfileResponse:
    updates: dict[str, str | None] = {}
    if body.email is not None:
        clean = body.email.strip()
        updates["MAT_LEGAL_EMAIL"] = clean or None
        updates["CAPCORE_NOTIFY_EMAIL"] = clean or None
    if body.siret is not None:
        clean = body.siret.strip()
        updates["MAT_SIRET"] = clean or None
    if body.kbis_media_id is not None:
        clean = body.kbis_media_id.strip()
        updates["MAT_KBIS_MEDIA_ID"] = clean or None

    if updates:
        upsert_env_vars(updates)
        refresh_settings()

    return await get_profile()
