# backend/api/routes/portal_onboarding.py
# Routes onboarding portail — MAJ62

from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.portal_onboarding_agent import (
    PortalOnboardingAgent,
    create_portal_account,
    mark_onboarding_done,
    request_password_reset,
    reset_password,
)
from config import get_settings, plain_secret_str
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


class DelegateRequest(BaseModel):
    client_id: str
    site_id: str


class BackToAutonomeRequest(BaseModel):
    client_id: str


class ModificationRequest(BaseModel):
    client_id: str
    site_id: str
    type_modification: str
    description: str
    priorite: str = "normale"


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


@router.post("/delegate-to-capcore")
async def delegate_to_capcore(body: DelegateRequest):
    """Client demande la gestion déléguée — annule Stripe + bascule management_plan."""
    try:
        supabase = get_supabase()

        client_res = (
            supabase.table("portal_clients")
            .select(
                "id, email, full_name, stripe_subscription_id, subscription_status, plan"
            )
            .eq("id", body.client_id)
            .single()
            .execute()
        )
        client = client_res.data
        if not client:
            raise HTTPException(404, "Client introuvable")

        site_res = (
            supabase.table("portal_sites")
            .select("id, site_name, site_url")
            .eq("id", body.site_id)
            .single()
            .execute()
        )
        site = site_res.data

        stripe_sub_id = client.get("stripe_subscription_id")
        if stripe_sub_id and client.get("subscription_status") == "active":
            try:
                import stripe

                stripe.api_key = plain_secret_str(get_settings().stripe_secret_key)
                stripe.Subscription.cancel(stripe_sub_id)
            except Exception:
                pass

        supabase.table("portal_clients").update(
            {
                "management_plan": "gere",
                "subscription_status": "none",
                "plan": "none",
            }
        ).eq("id", body.client_id).execute()

        existing = (
            supabase.table("portal_management_plans")
            .select("id")
            .eq("client_id", body.client_id)
            .execute()
        )
        if not existing.data:
            supabase.table("portal_management_plans").insert(
                {
                    "client_id": body.client_id,
                    "price_eur": 49.0,
                    "status": "active",
                    "modifications_per_month": 2,
                }
            ).execute()

        agent = PortalOnboardingAgent()
        site_name = site.get("site_name", "votre site") if site else "votre site"
        site_url = site.get("site_url", "") if site else ""
        agent.send_delegation_request_email(
            client.get("email", ""),
            client.get("full_name", ""),
            site_url,
            site_name,
        )
        agent.send_delegation_confirmation_email(
            client.get("email", ""),
            client.get("full_name", ""),
            site_name,
        )

        return {"success": True, "management_plan": "gere"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/back-to-autonome")
async def back_to_autonome(body: BackToAutonomeRequest):
    """Mat repasse un client en mode autonome — côté CyberForge uniquement."""
    try:
        supabase = get_supabase()

        client_res = (
            supabase.table("portal_clients")
            .select("id, email, full_name")
            .eq("id", body.client_id)
            .single()
            .execute()
        )
        client = client_res.data
        if not client:
            raise HTTPException(404, "Client introuvable")

        site_res = (
            supabase.table("portal_sites")
            .select("site_name")
            .eq("client_id", body.client_id)
            .limit(1)
            .execute()
        )
        site_name = site_res.data[0]["site_name"] if site_res.data else "votre site"

        supabase.table("portal_clients").update(
            {"management_plan": "autonome"}
        ).eq("id", body.client_id).execute()

        supabase.table("portal_management_plans").update(
            {"status": "inactive"}
        ).eq("client_id", body.client_id).execute()

        agent = PortalOnboardingAgent()
        agent.send_back_to_autonome_email(
            client.get("email", ""),
            client.get("full_name", ""),
            site_name,
        )

        return {"success": True, "management_plan": "autonome"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/modification-request")
async def modification_request(body: ModificationRequest):
    """Client géré soumet une demande de modification à Mat."""
    try:
        supabase = get_supabase()

        client_res = (
            supabase.table("portal_clients")
            .select("id, email, full_name, management_plan")
            .eq("id", body.client_id)
            .single()
            .execute()
        )
        client = client_res.data
        if not client:
            raise HTTPException(404, "Client introuvable")

        if client.get("management_plan") != "gere":
            raise HTTPException(403, "Réservé aux clients en gestion déléguée")

        site_res = (
            supabase.table("portal_sites")
            .select("site_name, site_url")
            .eq("id", body.site_id)
            .single()
            .execute()
        )
        site = site_res.data

        agent = PortalOnboardingAgent()
        agent.send_modification_request_email(
            client_email=client.get("email", ""),
            client_name=client.get("full_name", ""),
            site_name=site.get("site_name", "") if site else "",
            site_url=site.get("site_url", "") if site else "",
            type_modification=body.type_modification,
            description=body.description,
            priorite=body.priorite,
        )

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
