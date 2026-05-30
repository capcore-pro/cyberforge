"""
Service Stripe centralisé — clé par projet (stripe_configs) ou CapCore par défaut (.env).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Literal

import stripe

from config import get_settings, plain_secret_str
from stripe_db import (
    add_subscription,
    add_transaction,
    decrypt_config_secret,
    get_config_by_project,
    get_subscription,
    get_transaction_by_payment_intent,
    get_transaction_by_session,
    list_subscriptions,
    list_transactions,
    update_subscription,
    update_transaction,
)

logger = logging.getLogger(__name__)

_CAPCORE_FALLBACK_PROJECT = "capcore"
CheckoutMode = Literal["payment", "subscription"]
SubscriptionInterval = Literal["day", "week", "month", "year"]


class StripeServiceError(Exception):
    """Erreur métier Stripe."""


@dataclass(frozen=True)
class _StripeContext:
    project_id: str
    stripe_config_id: str
    currency: str
    api_key: str
    webhook_secret: str | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_secret_key() -> str:
    return plain_secret_str(get_settings().stripe_secret_key)


def _default_webhook_secret() -> str:
    settings = get_settings()
    for attr in (
        "stripe_webhook_secret",
        "stripe_desktop_webhook_secret",
        "stripe_ecommerce_webhook_secret",
    ):
        value = plain_secret_str(getattr(settings, attr, None))
        if value:
            return value
    return ""


def _default_publishable_key() -> str:
    return (
        os.environ.get("STRIPE_PUBLIC_KEY", "").strip()
        or os.environ.get("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "").strip()
        or "pk_capcore_placeholder"
    )


def _project_has_configured_secret(project_id: str) -> bool:
    pid = (project_id or _CAPCORE_FALLBACK_PROJECT).strip()
    cfg = get_config_by_project(pid)
    if cfg and cfg.get("enabled"):
        secret = decrypt_config_secret(cfg.get("secret_key_encrypted"))
        if secret:
            return True
    return bool(_default_secret_key())


def _fake_checkout_session(*, reference_id: str, success_url: str) -> Any:
    """Session factice lorsque STRIPE_SECRET_KEY est absente (E2E / dev)."""
    sid = f"cs_test_fake_{reference_id.replace('-', '')[:24]}"
    return SimpleNamespace(
        id=sid,
        url=f"https://checkout.stripe.com/pay/{sid}",
        payment_intent=sid,
    )


def _get_or_create_capcore_fallback_config() -> dict[str, Any]:
    from stripe_db import add_config

    cfg = get_config_by_project(_CAPCORE_FALLBACK_PROJECT)
    if cfg:
        return cfg
    secret = _default_secret_key()
    if not secret:
        raise StripeServiceError(
            "STRIPE_SECRET_KEY manquante — impossible d'initialiser le compte CapCore."
        )
    return add_config(
        project_id=_CAPCORE_FALLBACK_PROJECT,
        project_name="CapCore (défaut)",
        publishable_key=_default_publishable_key(),
        secret_key=secret,
        mode="test",
    )


def _resolve_context(project_id: str | None) -> _StripeContext:
    pid = (project_id or _CAPCORE_FALLBACK_PROJECT).strip()
    cfg = get_config_by_project(pid)

    if cfg and cfg.get("enabled"):
        secret = decrypt_config_secret(cfg.get("secret_key_encrypted"))
        if secret:
            webhook = decrypt_config_secret(cfg.get("webhook_secret_encrypted"))
            return _StripeContext(
                project_id=pid,
                stripe_config_id=str(cfg["id"]),
                currency=str(cfg.get("currency") or "eur"),
                api_key=secret,
                webhook_secret=webhook or None,
            )

    if pid != _CAPCORE_FALLBACK_PROJECT:
        raise StripeServiceError(
            "Paiement client non configuré — renseignez les clés Stripe du client "
            "dans la fiche projet (section Paiement client)."
        )

    fallback = _get_or_create_capcore_fallback_config()
    secret = decrypt_config_secret(fallback.get("secret_key_encrypted")) or _default_secret_key()
    if not secret:
        raise StripeServiceError("Aucune clé secrète Stripe disponible pour ce projet.")

    webhook = decrypt_config_secret(fallback.get("webhook_secret_encrypted")) or _default_webhook_secret()

    return _StripeContext(
        project_id=pid,
        stripe_config_id=str(fallback["id"]),
        currency=str(fallback.get("currency") or "eur"),
        api_key=secret,
        webhook_secret=webhook or None,
    )


def get_stripe_client(project_id: str | None = None):
    """
    Retourne le module `stripe` avec `api_key` positionnée sur le projet ou CapCore.
    """
    ctx = _resolve_context(project_id)
    stripe.api_key = ctx.api_key
    return stripe


def _cents(amount_eur: float) -> int:
    return max(1, int(round(float(amount_eur) * 100)))


def _checkout_line_items(
    items: list[dict[str, Any]],
    *,
    currency: str,
    mode: CheckoutMode,
) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    for raw in items:
        name = str(raw.get("name") or "Article").strip()[:120]
        quantity = max(1, int(raw.get("quantity") or 1))
        unit_amount = raw.get("unit_amount")
        if unit_amount is None and raw.get("amount_eur") is not None:
            unit_amount = _cents(float(raw["amount_eur"]))
        if unit_amount is None:
            raise StripeServiceError("Chaque item doit avoir unit_amount ou amount_eur.")
        price_data: dict[str, Any] = {
            "currency": currency,
            "product_data": {"name": name},
            "unit_amount": int(unit_amount),
        }
        if mode == "subscription":
            interval = str(raw.get("interval") or "month").strip().lower()
            price_data["recurring"] = {"interval": interval}
        line_items.append({"price_data": price_data, "quantity": quantity})
    if not line_items:
        raise StripeServiceError("Au moins un article est requis.")
    return line_items


def create_checkout_session(
    project_id: str,
    items: list[dict[str, Any]],
    success_url: str,
    cancel_url: str,
    mode: CheckoutMode = "payment",
    *,
    customer_email: str | None = None,
    metadata: dict[str, str] | None = None,
    client_reference_id: str | None = None,
    shipping_address_collection: bool = False,
) -> Any:
    """Crée une session Stripe Checkout (paiement unique ou abonnement)."""
    ctx = _resolve_context(project_id)

    reference = (client_reference_id or str(uuid.uuid4())).strip()
    if not _project_has_configured_secret(project_id):
        return _fake_checkout_session(reference_id=reference, success_url=success_url)

    get_stripe_client(project_id)

    session_metadata: dict[str, str] = {
        "project_id": ctx.project_id,
        "stripe_config_id": ctx.stripe_config_id,
    }
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                session_metadata[str(key)[:40]] = str(value)[:500]

    params: dict[str, Any] = {
        "mode": mode,
        "success_url": success_url.strip(),
        "cancel_url": cancel_url.strip(),
        "line_items": _checkout_line_items(items, currency=ctx.currency, mode=mode),
        "metadata": session_metadata,
    }

    if client_reference_id:
        params["client_reference_id"] = client_reference_id.strip()

    if customer_email:
        email = customer_email.strip().lower()
        if "@" in email:
            params["customer_email"] = email

    if shipping_address_collection:
        params["shipping_address_collection"] = {"allowed_countries": ["FR"]}
        params["billing_address_collection"] = "required"

    session = stripe.checkout.Session.create(**params)

    amount_eur = sum(
        (int(li["price_data"]["unit_amount"]) * int(li["quantity"])) / 100.0
        for li in params["line_items"]
    )
    pi_id = str(getattr(session, "payment_intent", None) or session.id)
    pending_email = params.get("customer_email")
    try:
        add_transaction(
            stripe_config_id=ctx.stripe_config_id,
            project_id=ctx.project_id,
            stripe_payment_intent_id=pi_id,
            stripe_session_id=str(session.id),
            amount_eur=amount_eur,
            type="subscription" if mode == "subscription" else "one_shot",
            status="pending",
            customer_email=pending_email,
            description=str(items[0].get("name") if items else "Checkout"),
        )
    except Exception as exc:
        logger.warning("Enregistrement transaction pending échoué : %s", exc)

    return session


def create_payment_link(
    project_id: str,
    amount_eur: float,
    description: str,
    customer_email: str | None = None,
) -> str:
    """Génère un lien de paiement Stripe one-shot (factures, devis)."""
    ctx = _resolve_context(project_id)
    get_stripe_client(project_id)

    label = description.strip() or "Paiement"
    link = stripe.PaymentLink.create(
        line_items=[
            {
                "price_data": {
                    "currency": ctx.currency,
                    "product_data": {"name": label[:120]},
                    "unit_amount": _cents(amount_eur),
                },
                "quantity": 1,
            }
        ],
        metadata={
            "project_id": ctx.project_id,
            "stripe_config_id": ctx.stripe_config_id,
            "customer_email": (customer_email or "").strip().lower(),
        },
    )
    url = getattr(link, "url", None)
    if not url:
        raise StripeServiceError("Stripe n'a pas retourné d'URL de paiement.")
    return str(url)


def create_subscription_link(
    project_id: str,
    plan_name: str,
    amount_eur: float,
    interval: SubscriptionInterval = "month",
    customer_email: str | None = None,
) -> str:
    """Génère un lien de paiement pour un abonnement récurrent."""
    ctx = _resolve_context(project_id)
    get_stripe_client(project_id)

    name = plan_name.strip() or "Abonnement"
    link = stripe.PaymentLink.create(
        line_items=[
            {
                "price_data": {
                    "currency": ctx.currency,
                    "product_data": {"name": name[:120]},
                    "unit_amount": _cents(amount_eur),
                    "recurring": {"interval": interval},
                },
                "quantity": 1,
            }
        ],
        metadata={
            "project_id": ctx.project_id,
            "stripe_config_id": ctx.stripe_config_id,
            "plan_name": name,
            "customer_email": (customer_email or "").strip().lower(),
        },
    )
    url = getattr(link, "url", None)
    if not url:
        raise StripeServiceError("Stripe n'a pas retourné d'URL d'abonnement.")
    return str(url)


def _metadata_project_id(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    pid = str(metadata.get("project_id") or "").strip()
    return pid or None


def _session_amount_eur(session: dict[str, Any]) -> float:
    total = session.get("amount_total")
    if total is not None:
        return float(total) / 100.0
    return 0.0


def _handle_checkout_completed(event: dict[str, Any], fallback_project_id: str | None) -> None:
    session = event.get("data", {}).get("object") or {}
    session_id = str(session.get("id") or "")
    if not session_id:
        return

    metadata = session.get("metadata") or {}
    pid = _metadata_project_id(metadata) or fallback_project_id or _CAPCORE_FALLBACK_PROJECT
    ctx = _resolve_context(pid)

    email = None
    details = session.get("customer_details") or {}
    if isinstance(details, dict):
        email = details.get("email")
    email = (email or metadata.get("customer_email") or "").strip().lower() or None

    pi_id = str(session.get("payment_intent") or session_id)
    amount_eur = _session_amount_eur(session)
    mode = str(session.get("mode") or "payment")
    tx_type = "subscription" if mode == "subscription" else "one_shot"

    existing = get_transaction_by_session(session_id)
    if existing:
        update_transaction(
            existing["id"],
            status="paid",
            customer_email=email,
            amount_eur=amount_eur or existing.get("amount_eur"),
        )
    else:
        add_transaction(
            stripe_config_id=ctx.stripe_config_id,
            project_id=ctx.project_id,
            stripe_payment_intent_id=pi_id,
            stripe_session_id=session_id,
            amount_eur=amount_eur,
            type=tx_type,
            status="paid",
            customer_email=email,
            description="Checkout Stripe",
        )
        from routers.notifications import schedule_notify

        client_name = None
        if isinstance(details, dict):
            client_name = details.get("name")
        client_name = (
            (str(client_name).strip() if client_name else "")
            or (email or "")
            or "Client"
        )
        amount_label = (
            f"{amount_eur:.0f}€"
            if amount_eur == int(amount_eur)
            else f"{amount_eur:.2f}€"
        )
        schedule_notify(
            "Paiement reçu 💳",
            "payment_received",
            "success",
            f"{amount_label} — {client_name}",
            ctx.project_id,
        )

    if mode == "subscription":
        sub_stripe_id = str(session.get("subscription") or "")
        if sub_stripe_id:
            sub_row = get_subscription(sub_stripe_id)
            if not sub_row:
                add_subscription(
                    stripe_config_id=ctx.stripe_config_id,
                    project_id=ctx.project_id,
                    stripe_subscription_id=sub_stripe_id,
                    customer_email=email or "unknown@customer.local",
                    plan_name=str(metadata.get("plan_name") or "Abonnement"),
                    amount_eur=amount_eur,
                    status="active",
                )


def _handle_invoice_paid(event: dict[str, Any], fallback_project_id: str | None) -> None:
    invoice = event.get("data", {}).get("object") or {}
    pid = _metadata_project_id(invoice.get("metadata")) or fallback_project_id
    sub_stripe_id = str(invoice.get("subscription") or "")
    if not sub_stripe_id:
        return

    sub_row = get_subscription(sub_stripe_id)
    if sub_row:
        pid = pid or sub_row.get("project_id")

    ctx = _resolve_context(pid)
    amount_eur = float(invoice.get("amount_paid") or 0) / 100.0
    email = str(invoice.get("customer_email") or "").strip().lower() or None
    pi_id = str(invoice.get("payment_intent") or invoice.get("id") or sub_stripe_id)

    if not get_transaction_by_payment_intent(pi_id):
        add_transaction(
            stripe_config_id=ctx.stripe_config_id,
            project_id=ctx.project_id,
            stripe_payment_intent_id=pi_id,
            amount_eur=amount_eur,
            type="subscription",
            status="paid",
            customer_email=email,
            description="Facture abonnement",
        )

    period_end = invoice.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
    if sub_row and period_end:
        update_subscription(
            sub_row["id"],
            status="active",
            current_period_end=datetime.fromtimestamp(
                int(period_end), tz=timezone.utc
            ).isoformat(),
        )


def _handle_subscription_deleted(
    event: dict[str, Any],
    fallback_project_id: str | None,
) -> None:
    sub = event.get("data", {}).get("object") or {}
    sub_stripe_id = str(sub.get("id") or "")
    if not sub_stripe_id:
        return

    row = get_subscription(sub_stripe_id)
    if row:
        update_subscription(row["id"], status="cancelled")
        return

    pid = _metadata_project_id(sub.get("metadata")) or fallback_project_id
    if not pid:
        return
    ctx = _resolve_context(pid)
    email = str(sub.get("metadata", {}).get("customer_email") or "unknown@customer.local")
    add_subscription(
        stripe_config_id=ctx.stripe_config_id,
        project_id=ctx.project_id,
        stripe_subscription_id=sub_stripe_id,
        customer_email=email,
        plan_name="Abonnement",
        amount_eur=0.0,
        status="cancelled",
    )


def _handle_payment_intent_failed(
    event: dict[str, Any],
    fallback_project_id: str | None,
) -> None:
    pi = event.get("data", {}).get("object") or {}
    pi_id = str(pi.get("id") or "")
    if not pi_id:
        return

    metadata = pi.get("metadata") or {}
    pid = _metadata_project_id(metadata) or fallback_project_id or _CAPCORE_FALLBACK_PROJECT
    ctx = _resolve_context(pid)

    existing = get_transaction_by_payment_intent(pi_id)
    amount_eur = float(pi.get("amount") or 0) / 100.0
    if existing:
        update_transaction(existing["id"], status="failed")
    else:
        add_transaction(
            stripe_config_id=ctx.stripe_config_id,
            project_id=ctx.project_id,
            stripe_payment_intent_id=pi_id,
            amount_eur=amount_eur,
            type="one_shot",
            status="failed",
            customer_email=metadata.get("customer_email"),
            description="Paiement échoué",
        )


def handle_webhook(
    payload: bytes | str,
    sig_header: str,
    project_id: str | None = None,
) -> dict[str, str]:
    """
    Vérifie la signature Stripe et traite les événements supportés.
    """
    ctx = _resolve_context(project_id)
    secret = ctx.webhook_secret or _default_webhook_secret()

    raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    if not secret:
        logger.warning("Webhook Stripe sans secret — mode dev (signature non vérifiée).")
        try:
            event_dict = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise StripeServiceError(f"Payload webhook invalide : {exc}") from exc
    else:
        try:
            event = stripe.Webhook.construct_event(raw, sig_header, secret)
        except stripe.error.SignatureVerificationError as exc:
            raise StripeServiceError("Signature webhook Stripe invalide.") from exc
        except ValueError as exc:
            raise StripeServiceError(f"Payload webhook invalide : {exc}") from exc

        if hasattr(event, "to_dict"):
            event_dict = event.to_dict()
        elif isinstance(event, dict):
            event_dict = event
        else:
            event_dict = dict(event)

    event_type = str(event_dict.get("type") or "")
    meta_pid = project_id
    obj = event_dict.get("data", {}).get("object") or {}
    if isinstance(obj, dict):
        meta_pid = _metadata_project_id(obj.get("metadata")) or meta_pid

    handlers = {
        "checkout.session.completed": _handle_checkout_completed,
        "invoice.paid": _handle_invoice_paid,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "payment_intent.payment_failed": _handle_payment_intent_failed,
    }

    handler = handlers.get(event_type)
    if not handler:
        return {"status": "ignored", "type": event_type}

    handler(event_dict, meta_pid)
    return {"status": "ok", "type": event_type}


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def cancel_subscription(subscription_id: str) -> dict[str, Any]:
    """Annule un abonnement côté Stripe et en base."""
    from stripe_db import get_subscription_by_id

    row = get_subscription_by_id(subscription_id)
    if row is None:
        raise StripeServiceError("Abonnement introuvable.")

    stripe_sub_id = str(row.get("stripe_subscription_id") or "")
    if not stripe_sub_id:
        raise StripeServiceError("stripe_subscription_id manquant.")

    get_stripe_client(str(row.get("project_id")))
    stripe.Subscription.cancel(stripe_sub_id)

    updated = update_subscription(subscription_id, status="cancelled")
    if updated is None:
        raise StripeServiceError("Mise à jour abonnement impossible.")
    return updated


def get_dashboard_data(project_id: str | None = None) -> dict[str, Any]:
    """Agrège transactions et abonnements pour le cockpit."""
    pid = project_id.strip() if project_id else None
    txs = list_transactions(project_id=pid, limit=500)
    subs = list_subscriptions(project_id=pid, limit=500)

    paid = [t for t in txs if t.get("status") == "paid"]
    total_collected = round(sum(float(t.get("amount_eur") or 0) for t in paid), 2)

    now = _utc_now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_month = 0.0
    for tx in paid:
        created = _parse_created_at(tx.get("created_at"))
        if created and created >= month_start:
            revenue_month += float(tx.get("amount_eur") or 0)
    revenue_month = round(revenue_month, 2)

    active_subs = [s for s in subs if s.get("status") == "active"]
    mrr = round(sum(float(s.get("amount_eur") or 0) for s in active_subs), 2)

    recent = sorted(
        txs,
        key=lambda t: str(t.get("created_at") or ""),
        reverse=True,
    )[:15]

    return {
        "project_id": pid,
        "total_collected_eur": total_collected,
        "revenue_this_month_eur": revenue_month,
        "active_subscriptions_count": len(active_subs),
        "active_subscriptions_mrr_eur": mrr,
        "recent_transactions": recent,
        "active_subscriptions": active_subs[:15],
    }
