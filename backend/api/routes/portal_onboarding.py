# backend/api/routes/portal_onboarding.py
# Routes onboarding portail — MAJ62

from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.portal_onboarding_agent import (
    create_portal_account,
    mark_onboarding_done,
    request_password_reset,
    reset_password,
)
from utils.supabase_client import get_supabase

router = APIRouter(prefix="/api/portal-onboarding", tags=["portal-onboarding"])


class CreateAccountRequest(BaseModel):
    email: str
    name: str
    site_url: str
    project_name: Optional[str] = "votre site"
    send_email: Optional[bool] = True


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class OnboardingDoneRequest(BaseModel):
    client_id: str
    management_plan: str  # 'autonome' | 'gere'


@router.post("/create-account")
async def create_account(req: CreateAccountRequest):
    """
    Crée un compte portail client + envoie email bienvenue.
    Appelé depuis CyberForge au moment de la livraison.
    """
    try:
        return create_portal_account(
            email=req.email,
            name=req.name,
            site_url=req.site_url,
            project_name=req.project_name or "votre site",
            send_email=req.send_email if req.send_email is not None else True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Demande de réinitialisation de mot de passe."""
    try:
        return request_password_reset(req.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reset-password")
async def reset_pwd(req: ResetPasswordRequest):
    """Réinitialisation du mot de passe avec token."""
    try:
        return reset_password(req.token, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/complete-onboarding")
async def complete_onboarding(req: OnboardingDoneRequest):
    """Marque l'onboarding terminé + enregistre le plan choisi."""
    try:
        return mark_onboarding_done(req.client_id, req.management_plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/check")
async def check_portal_account(site_url: str):
    """
    Vérifie si un compte portail existe déjà pour une URL de site.
    Appelé depuis CyberForge sur la fiche projet livré.
    """
    try:
        supabase = get_supabase()
        decoded_url = unquote(site_url)
        result = (
            supabase.table("portal_clients")
            .select(
                "id, email, full_name, subscription_status, onboarding_done, management_plan"
            )
            .eq("site_url", decoded_url)
            .execute()
        )

        if result.data:
            client = result.data[0]
            return {
                "exists": True,
                "client_id": client["id"],
                "email": client["email"],
                "name": client.get("full_name"),
                "subscription_status": client.get("subscription_status"),
                "onboarding_done": client.get("onboarding_done"),
                "management_plan": client.get("management_plan"),
            }
        return {"exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
