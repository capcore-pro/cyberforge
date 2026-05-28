"""
Stripe helpers for ecommerce (V1).

We avoid adding the `stripe` dependency; calls are done via Stripe REST API.
If STRIPE_SECRET_KEY is not configured, we return deterministic fake sessions so E2E can run.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

STRIPE_API = "https://api.stripe.com/v1"


class StripeEcommerceError(Exception):
    pass


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    url: str


def _secret(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return plain_secret_str(getattr(resolved, "stripe_secret_key", None))


def _webhook_secret(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return plain_secret_str(getattr(resolved, "stripe_ecommerce_webhook_secret", None))


def _headers(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}", "Content-Type": "application/x-www-form-urlencoded"}


def _fake_session(order_id: str) -> CheckoutSession:
    sid = f"cs_test_fake_{order_id.replace('-', '')[:24]}"
    return CheckoutSession(id=sid, url=f"https://checkout.stripe.com/pay/{sid}")


async def create_checkout_session(
    *,
    order_id: str,
    slug: str,
    success_url: str,
    cancel_url: str,
    currency: str,
    shipping_cents: int,
    line_items: list[dict[str, Any]],
    settings: Settings | None = None,
) -> CheckoutSession:
    secret = _secret(settings)
    if not secret:
        return _fake_session(order_id)

    # Stripe expects x-www-form-urlencoded with indexed keys.
    data: dict[str, str] = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "currency": currency.lower(),
        "client_reference_id": order_id,
        "metadata[order_id]": order_id,
        "metadata[slug]": slug,
        "shipping_address_collection[allowed_countries][0]": "FR",
        "billing_address_collection": "required",
    }

    # Shipping option (flat rate)
    if shipping_cents and shipping_cents > 0:
        data["shipping_options[0][shipping_rate_data][type]"] = "fixed_amount"
        data["shipping_options[0][shipping_rate_data][fixed_amount][amount]"] = str(int(shipping_cents))
        data["shipping_options[0][shipping_rate_data][fixed_amount][currency]"] = currency.lower()
        data["shipping_options[0][shipping_rate_data][display_name]"] = "Livraison"

    for i, li in enumerate(line_items):
        name = str(li["name"])
        amount = int(li["unit_amount"])
        qty = int(li["quantity"])
        data[f"line_items[{i}][price_data][currency]"] = currency.lower()
        data[f"line_items[{i}][price_data][product_data][name]"] = name[:120]
        data[f"line_items[{i}][price_data][unit_amount]"] = str(amount)
        data[f"line_items[{i}][quantity]"] = str(qty)

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{STRIPE_API}/checkout/sessions", headers=_headers(secret), data=data)
        if r.status_code >= 400:
            raise StripeEcommerceError(f"Stripe HTTP {r.status_code}: {r.text[:300]}")
        js = r.json()
        sid = js.get("id")
        url = js.get("url")
        if not sid or not url:
            raise StripeEcommerceError("Stripe session missing id/url.")
        return CheckoutSession(id=str(sid), url=str(url))


async def retrieve_session(*, session_id: str, settings: Settings | None = None) -> dict[str, Any]:
    secret = _secret(settings)
    if not secret:
        # Fake session shape
        return {"id": session_id, "payment_status": "paid" if "paid" in session_id else "unpaid"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{STRIPE_API}/checkout/sessions/{session_id}", headers=_headers(secret))
        if r.status_code >= 400:
            raise StripeEcommerceError(f"Stripe HTTP {r.status_code}: {r.text[:300]}")
        return r.json()


def verify_webhook_signature(
    *,
    payload_bytes: bytes,
    stripe_signature: str,
    settings: Settings | None = None,
) -> bool:
    secret = _webhook_secret(settings)
    if not secret:
        # Dev-mode: accept unsigned events (E2E-friendly).
        return True

    # Stripe signature header format: t=timestamp,v1=signature,...
    try:
        parts = {}
        for item in stripe_signature.split(","):
            k, v = item.split("=", 1)
            parts.setdefault(k, []).append(v)
        ts = int(parts.get("t", ["0"])[0])
        sigs = parts.get("v1", [])
    except Exception:
        return False

    signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    # basic replay protection window (5 minutes)
    if abs(int(time.time()) - ts) > 5 * 60:
        return False
    return any(hmac.compare_digest(expected, s) for s in sigs)

