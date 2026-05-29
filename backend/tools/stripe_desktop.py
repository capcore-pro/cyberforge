"""
Stripe Checkout + webhooks pour les mini-apps desktop CapCore.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str
from tools.stripe_ecommerce import (
    STRIPE_API,
    CheckoutSession,
    StripeEcommerceError,
    _fake_session,
    _headers,
    _secret,
)

logger = logging.getLogger(__name__)


def _desktop_webhook_secret(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return plain_secret_str(getattr(resolved, "stripe_desktop_webhook_secret", None))


def verify_desktop_webhook_signature(
    *,
    payload_bytes: bytes,
    stripe_signature: str,
    settings: Settings | None = None,
) -> bool:
    """Vérifie la signature Stripe avec STRIPE_DESKTOP_WEBHOOK_SECRET."""
    secret = _desktop_webhook_secret(settings)
    if not secret:
        # Dev / E2E : pas de secret configuré
        return True

    import hashlib
    import hmac

    try:
        parts: dict[str, list[str]] = {}
        for item in stripe_signature.split(","):
            key, value = item.split("=", 1)
            parts.setdefault(key, []).append(value)
        ts = int(parts.get("t", ["0"])[0])
        sigs = parts.get("v1", [])
    except Exception:
        return False

    signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if abs(int(time.time()) - ts) > 5 * 60:
        return False
    return any(hmac.compare_digest(expected, sig) for sig in sigs)


async def create_desktop_checkout_session(
    *,
    order_id: str,
    app_type: str,
    app_title: str,
    client_email: str,
    price_cents: int,
    success_url: str,
    cancel_url: str,
    settings: Settings | None = None,
) -> CheckoutSession:
    """Crée une session Stripe Checkout en mode paiement unique."""
    secret = _secret(settings)
    if not secret:
        return _fake_session(order_id)

    amount = max(50, int(price_cents))
    data: dict[str, str] = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "currency": "eur",
        "client_reference_id": order_id,
        "customer_email": client_email.strip().lower(),
        "metadata[order_id]": order_id,
        "metadata[app_type]": app_type,
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][product_data][name]": app_title[:120],
        "line_items[0][price_data][unit_amount]": str(amount),
        "line_items[0][quantity]": "1",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{STRIPE_API}/checkout/sessions",
            headers=_headers(secret),
            data=data,
        )
        if response.status_code >= 400:
            raise StripeEcommerceError(
                f"Stripe HTTP {response.status_code}: {response.text[:300]}"
            )
        payload = response.json()
        session_id = payload.get("id")
        url = payload.get("url")
        if not session_id or not url:
            raise StripeEcommerceError("Stripe session missing id/url.")
        return CheckoutSession(id=str(session_id), url=str(url))


async def retrieve_checkout_session(
    session_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    secret = _secret(settings)
    if not secret:
        return {"id": session_id, "payment_status": "paid"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{STRIPE_API}/checkout/sessions/{session_id}",
            headers=_headers(secret),
        )
        if response.status_code >= 400:
            raise StripeEcommerceError(
                f"Stripe HTTP {response.status_code}: {response.text[:300]}"
            )
        return response.json()
