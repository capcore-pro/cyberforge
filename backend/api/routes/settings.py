"""
Paramètres profil CapCore — JSON local + sync .env (email, siret).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import get_settings, refresh_settings
from security.env_file import read_env_value, upsert_env_vars
from security.profile_store import load_profile, save_profile

router = APIRouter(tags=["settings"])


class ProfileResponse(BaseModel):
    first_name: str = "Mat"
    last_name: str = ""
    title: str = "Fondateur CapCore"
    email: str = ""
    phone: str = ""
    siret: str = ""
    vat_number: str = ""
    address_street: str = ""
    address_postal_code: str = ""
    address_city: str = ""
    signature: str = ""
    kbis_media_id: str | None = None


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    siret: str | None = Field(default=None, max_length=20)
    vat_number: str | None = Field(default=None, max_length=32)
    address_street: str | None = Field(default=None, max_length=200)
    address_postal_code: str | None = Field(default=None, max_length=16)
    address_city: str | None = Field(default=None, max_length=80)
    signature: str | None = Field(default=None, max_length=2000)
    kbis_media_id: str | None = Field(default=None, max_length=64)


def _merge_env_defaults(stored: dict) -> ProfileResponse:
    settings = get_settings()
    email = (
        (stored.get("email") or "").strip()
        or (settings.mat_legal_email or settings.capcore_notify_email or "").strip()
    )
    siret = (stored.get("siret") or "").strip() or (settings.mat_siret or "").strip()
    kbis_id = stored.get("kbis_media_id") or read_env_value("MAT_KBIS_MEDIA_ID")
    return ProfileResponse(
        first_name=(stored.get("first_name") or "Mat").strip() or "Mat",
        last_name=(stored.get("last_name") or "").strip(),
        title=(stored.get("title") or "Fondateur CapCore").strip() or "Fondateur CapCore",
        email=email,
        phone=(stored.get("phone") or "").strip(),
        siret=siret,
        vat_number=(stored.get("vat_number") or "").strip(),
        address_street=(stored.get("address_street") or "").strip(),
        address_postal_code=(stored.get("address_postal_code") or "").strip(),
        address_city=(stored.get("address_city") or "").strip(),
        signature=(stored.get("signature") or "").strip(),
        kbis_media_id=kbis_id,
    )


@router.get("/settings/profile", response_model=ProfileResponse)
async def get_profile() -> ProfileResponse:
    return _merge_env_defaults(load_profile())


@router.post("/settings/profile", response_model=ProfileResponse)
async def post_profile(body: ProfileUpdateRequest) -> ProfileResponse:
    return await _apply_profile_update(body)


@router.patch("/settings/profile", response_model=ProfileResponse)
async def patch_profile(body: ProfileUpdateRequest) -> ProfileResponse:
    return await _apply_profile_update(body)


async def _apply_profile_update(body: ProfileUpdateRequest) -> ProfileResponse:
    updates: dict[str, str | None] = {}
    payload = body.model_dump(exclude_unset=True)
    json_updates: dict = {}

    for key, value in payload.items():
        if key == "kbis_media_id":
            clean = (value or "").strip() if value is not None else None
            json_updates[key] = clean or None
            if value is not None:
                updates["MAT_KBIS_MEDIA_ID"] = clean or None
            continue
        if value is None:
            continue
        clean = value.strip() if isinstance(value, str) else value
        json_updates[key] = clean

    if body.email is not None:
        email_clean = body.email.strip()
        updates["MAT_LEGAL_EMAIL"] = email_clean or None
        updates["CAPCORE_NOTIFY_EMAIL"] = email_clean or None
    if body.siret is not None:
        updates["MAT_SIRET"] = body.siret.strip() or None

    if json_updates:
        save_profile(json_updates)
    if updates:
        upsert_env_vars(updates)
        refresh_settings()

    return _merge_env_defaults(load_profile())
