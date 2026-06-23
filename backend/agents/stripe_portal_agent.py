# backend/agents/stripe_portal_agent.py
# Stripe abonnements Portail Client — MAJ61

from __future__ import annotations

import logging
import os

import stripe
from datetime import datetime, timezone
from typing import Any

from utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Plans CyberForge Portail
PLANS: dict[str, dict[str, Any]] = {
    "essentiel": {
        "name": "Essentiel",
        "description": "1 site — Édition textes & photos — Redéploiement auto",
        "features": [
            "1 site inclus",
            "Édition des textes en 1 clic",
            "Remplacement des photos",
            "Redéploiement Cloudflare automatique (~10s)",
            "Hébergement inclus",
            "SSL + domaine personnalisé",
            "Support email",
        ],
        "monthly_price_eur": 29,
        "yearly_price_eur": 249,
        "max_sites": 1,
        "can_edit_sections": False,
        "can_edit_colors": False,
        "can_edit_fonts": False,
        "priority_support": False,
    },
    "business": {
        "name": "Business",
        "description": "2 sites — Édition avancée sections, couleurs, fonts",
        "features": [
            "2 sites inclus",
            "Tout Essentiel inclus",
            "Ajout / suppression de sections",
            "Personnalisation couleurs & typographies",
            "Déploiement groupé multi-sites",
            "Statistiques de visites",
            "Support prioritaire email",
        ],
        "monthly_price_eur": 59,
        "yearly_price_eur": 499,
        "max_sites": 2,
        "can_edit_sections": True,
        "can_edit_colors": True,
        "can_edit_fonts": True,
        "priority_support": False,
    },
    "studio": {
        "name": "Studio",
        "description": "5 sites — Multi-sites + support prioritaire Mat",
        "features": [
            "5 sites inclus",
            "Tout Business inclus",
            "Gestion multi-sites en un tableau de bord",
            "Déploiement groupé tous sites en 1 clic",
            "Analytics avancées par site",
            "Chat support direct avec Mat",
            "Interventions ponctuelles incluses (2h/mois)",
            "Accès bêta nouvelles fonctionnalités",
        ],
        "monthly_price_eur": 119,
        "yearly_price_eur": 990,
        "max_sites": 5,
        "can_edit_sections": True,
        "can_edit_colors": True,
        "can_edit_fonts": True,
        "priority_support": True,
    },
}

TRIAL_DAYS = 14


def _get_stripe():
    """Initialise Stripe avec la clé API."""
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise ValueError("STRIPE_SECRET_KEY non configurée")
    stripe.api_key = key
    return stripe


def is_live_mode() -> bool:
    """Stripe est en mode live uniquement si STRIPE_LIVE_MODE=true en production."""
    return (
        os.getenv("APP_ENV") == "production"
        and os.getenv("STRIPE_LIVE_MODE", "false").lower() == "true"
    )


def check_portal_access(client: dict) -> dict:
    """
    Vérifie si un client a accès à l'éditeur.
    En mode test (STRIPE_LIVE_MODE != true) : toujours autorisé.
    En mode live : vérifie trial + abonnement actif.
    """
    if not is_live_mode():
        return {
            "has_access": True,
            "reason": "test_mode",
            "plan": client.get("plan", "trial"),
            "status": client.get("subscription_status", "trial"),
        }

    status = client.get("subscription_status", "none")
    plan = client.get("plan", "none")

    # Trial actif
    if status == "trial":
        trial_ends = client.get("trial_ends_at")
        if trial_ends:
            ends_dt = datetime.fromisoformat(str(trial_ends).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < ends_dt:
                days_left = (ends_dt - datetime.now(timezone.utc)).days
                return {
                    "has_access": True,
                    "reason": "trial_active",
                    "plan": "trial",
                    "status": "trial",
                    "trial_days_left": days_left,
                }
            _expire_trial(str(client["id"]))
            return {
                "has_access": False,
                "reason": "trial_expired",
                "plan": "none",
                "status": "expired",
            }

    # Abonnement actif
    if status == "active":
        return {
            "has_access": True,
            "reason": "subscription_active",
            "plan": plan,
            "status": "active",
            "plan_features": PLANS.get(plan, {}),
        }

    # Tout le reste : pas d'accès
    return {
        "has_access": False,
        "reason": status,
        "plan": plan,
        "status": status,
    }


def _expire_trial(client_id: str) -> None:
    """Met à jour le statut trial expiré en BDD."""
    try:
        supabase = get_supabase()
        supabase.table("portal_clients").update(
            {"subscription_status": "expired", "plan": "none"}
        ).eq("id", client_id).execute()
    except Exception as e:
        logger.error("[StripePortalAgent] Erreur expiration trial: %s", e)


def create_checkout_session(
    client_id: str,
    plan: str,
    interval: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """
    Crée une session Stripe Checkout pour souscrire à un plan.
    interval : 'monthly' | 'yearly'
    """
    if plan not in PLANS:
        raise ValueError(f"Plan inconnu : {plan}")
    if interval not in ("monthly", "yearly"):
        raise ValueError(f"Intervalle inconnu : {interval}")

    s = _get_stripe()
    supabase = get_supabase()

    result = (
        supabase.table("portal_clients").select("*").eq("id", client_id).single().execute()
    )
    if not result.data:
        raise ValueError(f"Client introuvable : {client_id}")
    client = result.data

    stripe_customer_id = client.get("stripe_customer_id")
    if not stripe_customer_id:
        customer = s.Customer.create(
            email=client["email"],
            name=client.get("full_name") or client["email"],
            metadata={"client_id": client_id, "cyberforge": "portal"},
        )
        stripe_customer_id = customer["id"]
        supabase.table("portal_clients").update(
            {"stripe_customer_id": stripe_customer_id}
        ).eq("id", client_id).execute()

    price_key = f"STRIPE_PRICE_{plan.upper()}_{interval.upper()}"
    price_id = os.getenv(price_key)
    if not price_id:
        raise ValueError(f"Variable manquante : {price_key}")

    plan_info = PLANS[plan]
    session = s.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        subscription_data={
            "metadata": {
                "client_id": client_id,
                "plan": plan,
                "interval": interval,
            }
        },
        metadata={
            "client_id": client_id,
            "plan": plan,
            "interval": interval,
        },
        locale="fr",
        payment_method_types=["card"],
        allow_promotion_codes=True,
    )

    return {
        "checkout_url": session["url"],
        "session_id": session["id"],
        "plan": plan,
        "plan_name": plan_info["name"],
        "price_eur": plan_info[f"{interval}_price_eur"],
        "interval": interval,
    }


def create_customer_portal_session(client_id: str, return_url: str) -> dict:
    """
    Crée une session Stripe Customer Portal (gestion abonnement, facturation, annulation).
    """
    s = _get_stripe()
    supabase = get_supabase()

    result = (
        supabase.table("portal_clients")
        .select("stripe_customer_id")
        .eq("id", client_id)
        .single()
        .execute()
    )
    if not result.data or not result.data.get("stripe_customer_id"):
        raise ValueError("Aucun compte Stripe pour ce client")

    session = s.billing_portal.Session.create(
        customer=result.data["stripe_customer_id"],
        return_url=return_url,
    )
    return {"portal_url": session["url"]}


def get_subscription_status(client_id: str) -> dict:
    """Retourne le statut abonnement complet d'un client."""
    supabase = get_supabase()
    result = (
        supabase.table("portal_clients")
        .select(
            "id, email, plan, subscription_status, stripe_customer_id, "
            "stripe_subscription_id, trial_ends_at, subscription_ends_at, billing_interval"
        )
        .eq("id", client_id)
        .single()
        .execute()
    )

    if not result.data:
        raise ValueError("Client introuvable")

    client = result.data
    access = check_portal_access(client)

    # Calcul trial_days_left même en mode test
    if client.get("subscription_status") == "trial" and client.get("trial_ends_at"):
        try:
            ends_dt = datetime.fromisoformat(
                client["trial_ends_at"].replace("Z", "+00:00")
            )
            access["trial_days_left"] = max(0, (ends_dt - datetime.now(timezone.utc)).days)
        except Exception:
            access["trial_days_left"] = 0

    plan_info = PLANS.get(client.get("plan", "none"), {})

    return {
        **access,
        "client_id": client_id,
        "email": client["email"],
        "plan_details": plan_info,
        "trial_ends_at": client.get("trial_ends_at"),
        "subscription_ends_at": client.get("subscription_ends_at"),
        "billing_interval": client.get("billing_interval", "monthly"),
        "stripe_customer_id": client.get("stripe_customer_id"),
    }


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Traite les webhooks Stripe.
    Événements gérés :
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    s = _get_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET non configurée")

    try:
        event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Signature webhook invalide") from None

    event_type = event["type"]
    supabase = get_supabase()

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        client_id = session["metadata"].get("client_id")
        plan = session["metadata"].get("plan")
        interval = session["metadata"].get("interval", "monthly")
        sub_id = session.get("subscription")

        if client_id and plan:
            sub = s.Subscription.retrieve(sub_id) if sub_id else None
            period_end = None
            if sub:
                period_end = datetime.fromtimestamp(
                    sub["current_period_end"], tz=timezone.utc
                ).isoformat()

            supabase.table("portal_clients").update(
                {
                    "plan": plan,
                    "subscription_status": "active",
                    "stripe_subscription_id": sub_id,
                    "billing_interval": interval,
                    "subscription_ends_at": period_end,
                }
            ).eq("id", client_id).execute()

            plan_info = PLANS.get(plan, {})
            price_key = f"{interval}_price_eur"
            supabase.table("portal_subscriptions").insert(
                {
                    "client_id": client_id,
                    "stripe_subscription_id": sub_id,
                    "stripe_customer_id": session.get("customer"),
                    "plan": plan,
                    "billing_interval": interval,
                    "status": "active",
                    "amount_eur": plan_info.get(price_key),
                    "period_start": datetime.now(timezone.utc).isoformat(),
                    "period_end": period_end,
                }
            ).execute()

    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        sub_id = sub["id"]
        status = sub["status"]
        period_end = datetime.fromtimestamp(
            sub["current_period_end"], tz=timezone.utc
        ).isoformat()

        status_map = {
            "active": "active",
            "past_due": "expired",
            "canceled": "canceled",
            "unpaid": "expired",
            "incomplete_expired": "expired",
        }
        cf_status = status_map.get(status, "expired")

        supabase.table("portal_clients").update(
            {"subscription_status": cf_status, "subscription_ends_at": period_end}
        ).eq("stripe_subscription_id", sub_id).execute()

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        sub_id = sub["id"]

        supabase.table("portal_clients").update(
            {
                "subscription_status": "canceled",
                "plan": "none",
                "stripe_subscription_id": None,
            }
        ).eq("stripe_subscription_id", sub_id).execute()

        supabase.table("portal_subscriptions").update(
            {"status": "canceled", "canceled_at": datetime.now(timezone.utc).isoformat()}
        ).eq("stripe_subscription_id", sub_id).execute()

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        sub_id = invoice.get("subscription")
        if sub_id:
            supabase.table("portal_clients").update(
                {"subscription_status": "expired"}
            ).eq("stripe_subscription_id", sub_id).execute()

    return {"received": True, "event": event_type}


def get_all_plans() -> dict:
    """Retourne tous les plans avec leurs features — utilisé par la page Pricing."""
    return {
        "plans": PLANS,
        "trial_days": TRIAL_DAYS,
        "currency": "EUR",
        "live_mode": is_live_mode(),
    }
