"""
Public storefront API for ecommerce projects.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from db.managed_projects_store import get_managed_projects_store
from stripe_service import StripeServiceError, create_checkout_session, handle_webhook

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ecommerce_public"])


def _not_configured() -> HTTPException:
    store = get_managed_projects_store()
    return HTTPException(
        status_code=503,
        detail={
            "message": "Supabase non configuré (SUPABASE_URL + SUPABASE_SECRET_KEY requis).",
            "diagnostics": store.connection_diagnostics(),
        },
    )


async def _get_project(slug: str) -> dict[str, Any]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    pid = await store.get_project_id_by_slug(slug=slug, type="ecommerce")
    if not pid:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    row = await store.get_project(pid)
    if not row or row.deleted_at:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    currency = (getattr(row, "ecommerce_currency", None) or "eur").strip().lower()
    shipping = getattr(row, "ecommerce_shipping_flat_cents", None)
    shipping_cents = int(shipping) if shipping is not None else 500
    return {
        "id": row.id,
        "slug": row.slug,
        "currency": currency or "eur",
        "shipping_flat_cents": max(0, shipping_cents),
    }


@router.get("/ecommerce/{slug}/products")
async def list_products(slug: str) -> list[dict[str, Any]]:
    project = await _get_project(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "active": "eq.true",
                "select": "id,sku,name,description,price_cents,currency,image_url,active,sort,stock_qty",
                "order": "sort.asc,name.asc",
            },
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        data = r.json()
        return data if isinstance(data, list) else []


class CartItem(BaseModel):
    product_id: str
    qty: int = Field(..., ge=1, le=99)


class CheckoutRequest(BaseModel):
    items: list[CartItem] = Field(default_factory=list)


class CheckoutResponse(BaseModel):
    order_id: str
    checkout_session_id: str
    checkout_url: str


@router.post("/ecommerce/{slug}/checkout", response_model=CheckoutResponse)
async def create_checkout(slug: str, body: CheckoutRequest) -> CheckoutResponse:
    project = await _get_project(slug)
    store = get_managed_projects_store()
    if not body.items:
        raise HTTPException(status_code=400, detail="Panier vide.")

    prod_url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch products involved
        ids = ",".join([f"\"{it.product_id}\"" for it in body.items])
        r = await client.get(
            prod_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "id": f"in.({ids})",
                "select": "id,name,price_cents,currency,active",
            },
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        products = {p["id"]: p for p in (r.json() or []) if isinstance(p, dict)}

    subtotal = 0
    line_items: list[dict[str, Any]] = []
    order_items: list[dict[str, Any]] = []
    for it in body.items:
        p = products.get(it.product_id)
        if not p or not p.get("active", True):
            raise HTTPException(status_code=400, detail="Produit invalide.")
        price = int(p["price_cents"])
        qty = int(it.qty)
        subtotal += price * qty
        line_items.append({"name": p["name"], "unit_amount": price, "quantity": qty})
        order_items.append(
            {
                "product_id": it.product_id,
                "name_snapshot": p["name"],
                "price_cents_snapshot": price,
                "qty": qty,
            }
        )

    shipping = int(project["shipping_flat_cents"])
    if shipping > 0:
        line_items.append({"name": "Livraison", "unit_amount": shipping, "quantity": 1})
    total = subtotal + shipping

    # Create order
    orders_url = f"{store._rest_url()}/ecommerce_orders"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        ro = await client.post(
            orders_url,
            headers=store._headers("return=representation"),  # noqa: SLF001
            json={
                "project_id": project["id"],
                "status": "pending",
                "subtotal_cents": subtotal,
                "shipping_cents": shipping,
                "total_cents": total,
                "currency": project["currency"],
            },
        )
        if ro.status_code >= 400:
            raise HTTPException(status_code=502, detail=ro.text[:200])
        order_row = (ro.json() or [{}])[0]
        order_id = order_row["id"]

    # Create order items
    items_url = f"{store._rest_url()}/ecommerce_order_items"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = []
        for oi in order_items:
            payload.append({"order_id": order_id, **oi})
        ri = await client.post(items_url, headers=store._headers(), json=payload)  # noqa: SLF001
        if ri.status_code >= 400:
            logger.warning("order_items insert failed: %s", ri.text[:200])

    success_url = f"https://{slug}.vercel.app/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"https://{slug}.vercel.app/cart"

    try:
        session = create_checkout_session(
            project_id=str(project["id"]),
            items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            mode="payment",
            client_reference_id=order_id,
            shipping_address_collection=True,
            metadata={"order_id": order_id, "slug": slug},
        )
    except StripeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Update order with session id
    async with httpx.AsyncClient(timeout=30.0) as client:
        rp = await client.patch(
            orders_url,
            headers=store._headers("return=representation"),  # noqa: SLF001
            params={"id": f"eq.{order_id}"},
            json={"stripe_checkout_session_id": session.id},
        )
        if rp.status_code >= 400:
            logger.warning("order update session_id failed: %s", rp.text[:200])

    return CheckoutResponse(order_id=order_id, checkout_session_id=session.id, checkout_url=session.url)


@router.get("/ecommerce/{slug}/checkout/{session_id}/status")
async def checkout_status(slug: str, session_id: str) -> dict[str, Any]:
    project = await _get_project(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_orders"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "stripe_checkout_session_id": f"eq.{session_id}",
                "select": "id,status,total_cents,currency,created_at",
                "limit": "1",
            },
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        rows = r.json()
        if not rows:
            raise HTTPException(status_code=404, detail="Order introuvable.")
        return rows[0]


@router.post("/ecommerce/{slug}/stripe/webhook")
async def stripe_webhook(
    slug: str,
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    project = await _get_project(slug)
    payload = await request.body()

    try:
        result = handle_webhook(
            payload,
            stripe_signature or "",
            project_id=str(project["id"]),
        )
    except StripeServiceError as exc:
        detail = str(exc)
        status = 400 if "invalide" in detail.lower() else 502
        raise HTTPException(status_code=status, detail=detail) from exc

    if result.get("type") != "checkout.session.completed":
        return result

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return result

    obj = (event.get("data") or {}).get("object") or {}
    session_id = obj.get("id")
    if not session_id:
        return result

    store = get_managed_projects_store()
    orders_url = f"{store._rest_url()}/ecommerce_orders"  # noqa: SLF001
    patch: dict[str, Any] = {"status": "paid"}
    if obj.get("customer_details"):
        patch["customer_email"] = (obj["customer_details"].get("email") or None)
        patch["customer_name"] = (obj["customer_details"].get("name") or None)
    if obj.get("shipping_details") and obj["shipping_details"].get("address"):
        patch["shipping_address_json"] = obj["shipping_details"]["address"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            orders_url,
            headers=store._headers(),  # noqa: SLF001
            params={"stripe_checkout_session_id": f"eq.{session_id}"},
            json=patch,
        )
        if r.status_code >= 400:
            logger.warning("webhook order update failed: %s", r.text[:200])
    return {"status": "ok", "type": "checkout.session.completed"}

