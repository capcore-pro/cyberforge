"""
API Stripe — configuration par projet, paiements, webhooks, dashboard.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Header, Query, Request
from pydantic import BaseModel, Field

import stripe_db as db
from config import get_settings, plain_secret_str, refresh_settings
from security.env_file import upsert_env_vars
from stripe_service import (
    StripeServiceError,
    cancel_subscription,
    create_checkout_session,
    create_payment_link,
    create_subscription_link,
    get_dashboard_data,
    handle_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stripe"])

_CAPCORE_PROJECT_ID = "capcore"

StripeMode = Literal["test", "live"]
CheckoutMode = Literal["payment", "subscription"]
TransactionStatus = Literal["pending", "paid", "failed", "refunded"]
TransactionType = Literal["one_shot", "subscription"]
SubscriptionStatus = Literal["active", "cancelled", "past_due"]
SubscriptionInterval = Literal["day", "week", "month", "year"]


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _stripe_error(exc: StripeServiceError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


def _mask_config(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if out.get("secret_key_encrypted"):
        out["secret_key_encrypted"] = "***"
    if out.get("webhook_secret_encrypted"):
        out["webhook_secret_encrypted"] = "***"
    return out


# --- Schémas ---


class ConfigCreateBody(BaseModel):
    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    publishable_key: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)
    webhook_secret: str | None = None
    mode: StripeMode = "test"
    currency: str = "eur"
    enabled: bool = True


class ConfigUpdateBody(BaseModel):
    project_id: str | None = Field(default=None, min_length=1)
    project_name: str | None = Field(default=None, min_length=1)
    publishable_key: str | None = Field(default=None, min_length=1)
    secret_key: str | None = None
    webhook_secret: str | None = None
    mode: StripeMode | None = None
    currency: str | None = None
    enabled: bool | None = None


class CheckoutItemBody(BaseModel):
    name: str = Field(min_length=1)
    amount_eur: float | None = Field(default=None, ge=0)
    unit_amount: int | None = Field(default=None, ge=1)
    quantity: int = Field(default=1, ge=1)
    interval: SubscriptionInterval | None = None


class CheckoutBody(BaseModel):
    project_id: str = Field(min_length=1)
    items: list[CheckoutItemBody] = Field(min_length=1)
    customer_email: str = Field(min_length=3)
    success_url: str = Field(min_length=1)
    cancel_url: str = Field(min_length=1)
    mode: CheckoutMode = "payment"


class PaymentLinkBody(BaseModel):
    project_id: str = Field(min_length=1)
    amount_eur: float = Field(gt=0)
    description: str = Field(min_length=1)
    customer_email: str | None = None


class SubscriptionLinkBody(BaseModel):
    project_id: str = Field(min_length=1)
    plan_name: str = Field(min_length=1)
    amount_eur: float = Field(gt=0)
    interval: SubscriptionInterval = "month"
    customer_email: str | None = None


class CapcoreStripeBody(BaseModel):
    secret_key: str = Field(min_length=1)
    publishable_key: str | None = None
    webhook_secret: str | None = None
    mode: StripeMode = "test"


class ClientStripeBody(BaseModel):
    secret_key: str = Field(min_length=1)
    webhook_secret: str | None = None
    publishable_key: str | None = None
    mode: StripeMode = "test"
    project_name: str | None = None


def _capcore_configured() -> bool:
    cfg = db.get_config_by_project(_CAPCORE_PROJECT_ID)
    if cfg and cfg.get("enabled"):
        secret = db.decrypt_config_secret(cfg.get("secret_key_encrypted"))
        if secret:
            return True
    return bool(plain_secret_str(get_settings().stripe_secret_key))


def _client_configured(project_id: str) -> bool:
    cfg = db.get_config_by_project(project_id.strip())
    if not cfg or not cfg.get("enabled"):
        return False
    return bool(db.decrypt_config_secret(cfg.get("secret_key_encrypted")))


def _infer_publishable_key(secret_key: str, override: str | None) -> str:
    if override and override.strip():
        return override.strip()
    sk = secret_key.strip()
    if sk.startswith("sk_live"):
        return "pk_live_configured"
    return "pk_test_configured"


# --- CapCore (mes revenus) ---


@router.get("/capcore")
async def get_capcore_stripe() -> dict[str, Any]:
    cfg = db.get_config_by_project(_CAPCORE_PROJECT_ID)
    return {
        "configured": _capcore_configured(),
        "config": _mask_config(cfg) if cfg else None,
    }


@router.put("/capcore")
async def upsert_capcore_stripe(body: CapcoreStripeBody) -> dict[str, Any]:
    pk = _infer_publishable_key(body.secret_key, body.publishable_key)
    try:
        row = db.upsert_config_by_project(
            project_id=_CAPCORE_PROJECT_ID,
            project_name="CapCore — Mes revenus",
            publishable_key=pk,
            secret_key=body.secret_key.strip(),
            webhook_secret=body.webhook_secret,
            mode=body.mode,
            enabled=True,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc

    upsert_env_vars({"STRIPE_SECRET_KEY": body.secret_key.strip()})
    refresh_settings()

    return {"configured": True, "config": _mask_config(row)}


# --- Client (par projet déployé) ---


@router.get("/projects/{project_id}")
async def get_client_stripe(project_id: str) -> dict[str, Any]:
    pid = project_id.strip()
    cfg = db.get_config_by_project(pid)
    return {
        "project_id": pid,
        "configured": _client_configured(pid),
        "config": _mask_config(cfg) if cfg else None,
    }


@router.put("/projects/{project_id}")
async def upsert_client_stripe(
    project_id: str,
    body: ClientStripeBody,
) -> dict[str, Any]:
    pid = project_id.strip()
    name = (body.project_name or f"Client — {pid[:8]}").strip()
    pk = _infer_publishable_key(body.secret_key, body.publishable_key)
    try:
        row = db.upsert_config_by_project(
            project_id=pid,
            project_name=name,
            publishable_key=pk,
            secret_key=body.secret_key.strip(),
            webhook_secret=body.webhook_secret,
            mode=body.mode,
            enabled=True,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc
    return {
        "project_id": pid,
        "configured": True,
        "config": _mask_config(row),
    }


@router.post("/projects/{project_id}/apply")
async def apply_client_stripe(project_id: str) -> dict[str, Any]:
    """Active la config client pour les paiements du projet (backend CyberForge)."""
    pid = project_id.strip()
    if not _client_configured(pid):
        raise HTTPException(
            status_code=400,
            detail="Clés Stripe client manquantes — enregistrez-les avant d'appliquer.",
        )
    cfg = db.get_config_by_project(pid)
    if cfg and not cfg.get("enabled"):
        db.update_config(str(cfg["id"]), enabled=True)
    return {
        "applied": True,
        "project_id": pid,
        "message": (
            "Clés Stripe client actives — les paiements du site utilisent "
            "le compte Stripe du client via le backend CyberForge."
        ),
    }


# --- Configs ---


@router.get("/configs")
async def list_stripe_configs() -> list[dict[str, Any]]:
    return [_mask_config(row) for row in db.list_configs()]


@router.post("/configs", status_code=201)
async def create_stripe_config(body: ConfigCreateBody) -> dict[str, Any]:
    try:
        row = db.add_config(
            project_id=body.project_id,
            project_name=body.project_name,
            publishable_key=body.publishable_key,
            secret_key=body.secret_key,
            webhook_secret=body.webhook_secret,
            mode=body.mode,
            currency=body.currency,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc
    return _mask_config(row)


@router.put("/configs/{config_id}")
async def update_stripe_config(config_id: str, body: ConfigUpdateBody) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = db.get_config(config_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Configuration introuvable.")
        return _mask_config(row)
    try:
        row = db.update_config(config_id, **fields)
    except ValueError as exc:
        raise _value_error(exc) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Configuration introuvable.")
    return _mask_config(row)


@router.delete("/configs/{config_id}")
async def delete_stripe_config(config_id: str) -> dict[str, bool]:
    if not db.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Configuration introuvable.")
    return {"ok": True}


# --- Paiements ---


@router.post("/checkout")
async def post_checkout(body: CheckoutBody) -> dict[str, Any]:
    items = [item.model_dump(exclude_none=True) for item in body.items]
    try:
        session = create_checkout_session(
            project_id=body.project_id,
            items=items,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            mode=body.mode,
            customer_email=body.customer_email,
        )
    except (ValueError, StripeServiceError) as exc:
        if isinstance(exc, ValueError):
            raise _value_error(exc) from exc
        raise _stripe_error(exc) from exc

    return {
        "session_id": str(session.id),
        "checkout_url": str(session.url),
        "mode": body.mode,
    }


@router.post("/payment-link")
async def post_payment_link(body: PaymentLinkBody) -> dict[str, str]:
    try:
        url = create_payment_link(
            project_id=body.project_id,
            amount_eur=body.amount_eur,
            description=body.description,
            customer_email=body.customer_email,
        )
    except (ValueError, StripeServiceError) as exc:
        if isinstance(exc, ValueError):
            raise _value_error(exc) from exc
        raise _stripe_error(exc) from exc
    return {"url": url}


@router.post("/subscription-link")
async def post_subscription_link(body: SubscriptionLinkBody) -> dict[str, str]:
    try:
        url = create_subscription_link(
            project_id=body.project_id,
            plan_name=body.plan_name,
            amount_eur=body.amount_eur,
            interval=body.interval,
            customer_email=body.customer_email,
        )
    except (ValueError, StripeServiceError) as exc:
        if isinstance(exc, ValueError):
            raise _value_error(exc) from exc
        raise _stripe_error(exc) from exc
    return {"url": url}


# --- Webhooks ---


@router.post("/webhook/capcore")
async def webhook_capcore(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    return await _process_webhook(request, stripe_signature, project_id="capcore")


@router.post("/webhook/{project_id}")
async def webhook_project(
    project_id: str,
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    return await _process_webhook(request, stripe_signature, project_id=project_id)


async def _process_webhook(
    request: Request,
    stripe_signature: str | None,
    *,
    project_id: str | None,
) -> dict[str, str]:
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="En-tête Stripe-Signature requis.")
    payload = await request.body()
    try:
        return handle_webhook(payload, stripe_signature, project_id=project_id)
    except StripeServiceError as exc:
        detail = str(exc)
        if "invalide" in detail.lower():
            raise HTTPException(status_code=400, detail=detail) from exc
        raise _stripe_error(exc) from exc


# --- Dashboard ---


@router.get("/dashboard")
async def dashboard_all() -> dict[str, Any]:
    return get_dashboard_data(project_id=None)


@router.get("/dashboard/{project_id}")
async def dashboard_project(project_id: str) -> dict[str, Any]:
    return get_dashboard_data(project_id=project_id)


# --- Transactions & abonnements ---


@router.get("/transactions")
async def list_stripe_transactions(
    project_id: str | None = Query(default=None),
    status: TransactionStatus | None = Query(default=None),
    type: TransactionType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    try:
        return db.list_transactions(
            project_id=project_id,
            status=status,
            type=type,
            limit=limit,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/subscriptions")
async def list_stripe_subscriptions(
    project_id: str | None = Query(default=None),
    status: SubscriptionStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    try:
        return db.list_subscriptions(project_id=project_id, status=status, limit=limit)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.put("/subscriptions/{subscription_id}/cancel")
async def cancel_stripe_subscription(subscription_id: str) -> dict[str, Any]:
    try:
        return cancel_subscription(subscription_id)
    except StripeServiceError as exc:
        if "introuvable" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise _stripe_error(exc) from exc
