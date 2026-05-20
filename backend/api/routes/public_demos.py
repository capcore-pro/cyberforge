"""
Routes publiques démos — accès client via lien + mot de passe (sans compte).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.demos_store import DemoPayload, get_demos_store

router = APIRouter(tags=["public-demos"])


class DemoUnlockRequest(BaseModel):
    password: str = Field(..., min_length=3, max_length=128)


class DemoMetaResponse(BaseModel):
    title: str
    expires_at: str
    expired: bool


class DemoUnlockResponse(BaseModel):
    title: str
    expires_at: str
    payload: DemoPayload


@router.get("/demos/{token}/meta", response_model=DemoMetaResponse)
async def public_demo_meta(token: str) -> DemoMetaResponse:
    """Métadonnées publiques (sans livrable ni mot de passe)."""
    store = get_demos_store()
    row = await store.get_by_token(token.strip())
    if row is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")
    meta = store.meta_from_row(row)
    return DemoMetaResponse(
        title=meta.title,
        expires_at=meta.expires_at,
        expired=meta.expired,
    )


@router.post("/demos/{token}/unlock", response_model=DemoUnlockResponse)
async def public_demo_unlock(
    token: str,
    body: DemoUnlockRequest,
) -> DemoUnlockResponse:
    """Vérifie le mot de passe et renvoie le livrable figé (lecture seule)."""
    store = get_demos_store()
    clean_token = token.strip()
    row = await store.get_by_token(clean_token)
    if row is None:
        raise HTTPException(status_code=404, detail="Démo introuvable.")

    if store.is_expired(row):
        raise HTTPException(
            status_code=410,
            detail="Cette démo a expiré. Demandez un nouveau lien à votre contact.",
        )

    unlocked = await store.unlock(clean_token, body.password)
    if unlocked is None:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect.")

    return DemoUnlockResponse(
        title=unlocked.title,
        expires_at=unlocked.expires_at,
        payload=unlocked.payload,
    )
