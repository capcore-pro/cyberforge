"""
API mini-apps desktop CapCore — commandes, Stripe Checkout, téléchargement.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from config import get_settings
from desktop_app_db import (
    create_order,
    get_order,
    get_order_by_session,
    get_order_by_token,
    list_orders,
    update_order,
)
from desktop_app_generator import DesktopAppGeneratorError, generate_exe
from tools.stripe_desktop import (
    StripeEcommerceError,
    create_desktop_checkout_session,
    verify_desktop_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["desktop"])

_SUPPORTED_APP_TYPES = frozenset({"facture_express", "lead_tracker", "caisse"})
_APP_TITLES: dict[str, str] = {
    "facture_express": "Facture Express",
    "lead_tracker": "Lead Tracker",
    "caisse": "Caisse CapCore",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_download_expired(order: dict[str, Any]) -> bool:
    expires_at = _parse_iso_dt(order.get("expires_at"))
    if expires_at is None:
        return False
    return _utc_now() > expires_at


def _capcore_site_base() -> str:
    settings = get_settings()
    base = (getattr(settings, "capcore_site_url", None) or "https://capcore.pro").strip()
    return base.rstrip("/")


def _spawn_generate_exe(order_id: str) -> None:
    def _worker() -> None:
        try:
            generate_exe(order_id)
        except DesktopAppGeneratorError as exc:
            logger.error("Génération desktop échouée — order=%s : %s", order_id, exc)
        except Exception:
            logger.exception("Génération desktop inattendue — order=%s", order_id)

    thread = threading.Thread(target=_worker, name=f"desktop-gen-{order_id[:8]}", daemon=True)
    thread.start()
    logger.info("Génération desktop lancée en arrière-plan — order=%s", order_id)


# --- Schémas ---


class CreateOrderBody(BaseModel):
    app_type: str = Field(min_length=1)
    client_email: str = Field(min_length=3)
    client_name: str | None = None
    price_cents: int = Field(ge=50, le=500_00)


class CreateOrderResponse(BaseModel):
    order_id: str
    checkout_url: str


class OrderStatusResponse(BaseModel):
    generation_status: str
    r2_url: str | None = None
    expires_at: str | None = None


# --- Routes ---


@router.post("/orders", response_model=CreateOrderResponse)
async def post_create_order(body: CreateOrderBody) -> CreateOrderResponse:
    app_type = body.app_type.strip().lower()
    if app_type not in _SUPPORTED_APP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"app_type invalide — valeurs : {', '.join(sorted(_SUPPORTED_APP_TYPES))}",
        )

    email = body.client_email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="client_email invalide.")

    order_id = str(uuid.uuid4())
    site = _capcore_site_base()
    success_url = f"{site}/apps/success?order_id={order_id}"
    cancel_url = f"{site}/apps?cancelled=1"

    try:
        session = await create_desktop_checkout_session(
            order_id=order_id,
            app_type=app_type,
            app_title=_APP_TITLES[app_type],
            client_email=email,
            price_cents=body.price_cents,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except StripeEcommerceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        create_order(
            app_type=app_type,
            client_email=email,
            stripe_session_id=session.id,
            client_name=body.client_name,
            order_id=order_id,
            generation_status="waiting",
            stripe_payment_status="pending",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateOrderResponse(order_id=order_id, checkout_url=session.url)


@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(order_id: str) -> OrderStatusResponse:
    order = get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    r2_url = order.get("r2_url")
    return OrderStatusResponse(
        generation_status=str(order.get("generation_status") or "waiting"),
        r2_url=str(r2_url) if r2_url and order.get("generation_status") == "ready" else None,
        expires_at=order.get("expires_at"),
    )


@router.get("/download/{download_token}")
async def download_by_token(download_token: str) -> RedirectResponse:
    order = get_order_by_token(download_token.strip())
    if order is None:
        raise HTTPException(status_code=404, detail="Lien de téléchargement invalide.")

    if _is_download_expired(order):
        raise HTTPException(status_code=410, detail="Ce lien de téléchargement a expiré.")

    if str(order.get("generation_status") or "") != "ready":
        raise HTTPException(
            status_code=409,
            detail="L'application n'est pas encore prête au téléchargement.",
        )

    r2_url = order.get("r2_url")
    if not r2_url:
        raise HTTPException(
            status_code=503,
            detail="Fichier de téléchargement indisponible.",
        )

    return RedirectResponse(url=str(r2_url), status_code=302)


@router.get("/orders")
async def get_orders_list(
    status: Literal["waiting", "generating", "ready", "failed"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Liste des commandes desktop (usage interne CyberForge)."""
    return list_orders(status=status, limit=limit)


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="En-tête Stripe-Signature requis.")

    if not verify_desktop_webhook_signature(
        payload_bytes=payload,
        stripe_signature=stripe_signature,
    ):
        raise HTTPException(status_code=400, detail="Signature Stripe invalide.")

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Payload JSON invalide.") from exc

    event_type = event.get("type")
    if event_type != "checkout.session.completed":
        return {"status": "ignored"}

    session_obj = (event.get("data") or {}).get("object") or {}
    session_id = str(session_obj.get("id") or "").strip()
    if not session_id:
        return {"status": "ignored"}

    order = get_order_by_session(session_id)
    if order is None:
        metadata = session_obj.get("metadata") or {}
        order_id = str(metadata.get("order_id") or "").strip()
        if order_id:
            order = get_order(order_id)
    if order is None:
        logger.warning("Webhook desktop — commande introuvable pour session %s", session_id)
        return {"status": "order_not_found"}

    order_id = str(order["id"])
    payment_status = str(order.get("stripe_payment_status") or "")
    gen_status = str(order.get("generation_status") or "")

    if payment_status == "paid" and gen_status in ("generating", "ready"):
        return {"status": "already_processed"}

    customer = session_obj.get("customer_details") or {}
    updates: dict[str, Any] = {"stripe_payment_status": "paid"}
    if customer.get("email"):
        updates["client_email"] = str(customer["email"]).strip().lower()
    if customer.get("name"):
        updates["client_name"] = str(customer["name"]).strip()

    update_order(order_id, **updates)

    if gen_status not in ("generating", "ready"):
        _spawn_generate_exe(order_id)

    return {"status": "ok"}
