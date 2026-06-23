# backend/api/routes/stripe_portal.py
# 5 routes Stripe Portail — MAJ61

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from agents.stripe_portal_agent import (
    create_checkout_session,
    create_customer_portal_session,
    get_all_plans,
    get_subscription_status,
    handle_webhook,
)

router = APIRouter(prefix="/api/stripe-portal", tags=["stripe-portal"])


class CheckoutRequest(BaseModel):
    client_id: str
    plan: str  # essentiel | business | studio
    interval: str  # monthly | yearly
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalSessionRequest(BaseModel):
    client_id: str
    return_url: Optional[str] = None


# GET /api/stripe-portal/plans
@router.get("/plans")
async def get_plans():
    """Retourne tous les plans avec features et prix — public."""
    try:
        return get_all_plans()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# GET /api/stripe-portal/status/{client_id}
@router.get("/status/{client_id}")
async def subscription_status(client_id: str):
    """Statut abonnement complet d'un client."""
    try:
        return get_subscription_status(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# POST /api/stripe-portal/create-checkout
@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest):
    """Crée une session Stripe Checkout — redirige vers page de paiement."""
    try:
        base_url = os.getenv("PORTAL_URL", "https://client.capcore.pro")
        success_url = req.success_url or f"{base_url}/subscription/success"
        cancel_url = req.cancel_url or f"{base_url}/pricing"

        result = create_checkout_session(
            client_id=req.client_id,
            plan=req.plan,
            interval=req.interval,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# POST /api/stripe-portal/customer-portal
@router.post("/customer-portal")
async def customer_portal(req: PortalSessionRequest):
    """Stripe Customer Portal — gérer/annuler abonnement."""
    try:
        base_url = os.getenv("PORTAL_URL", "https://client.capcore.pro")
        return_url = req.return_url or f"{base_url}/dashboard"
        return create_customer_portal_session(req.client_id, return_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# POST /api/stripe-portal/webhook
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    """
    Webhook Stripe — NE PAS protéger avec auth middleware.
    Stripe envoie la signature dans le header stripe-signature.
    """
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Header stripe-signature manquant")
    try:
        result = handle_webhook(payload, stripe_signature)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
