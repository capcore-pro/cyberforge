"""
E2E: create ecommerce project → wait deployed → seed products → public list → create checkout → simulate webhook → verify paid.
"""

from __future__ import annotations

import os
import time
from dotenv import load_dotenv

import httpx

BASE = (os.environ.get("BASE_URL") or "http://127.0.0.1:8002").rstrip("/")


def main() -> None:
    load_dotenv("backend/.env", override=False)

    slug = f"shope2e-{int(time.time())}"
    prompt = "Boutique V1: catalogue + panier + Stripe Checkout."
    c = httpx.Client(timeout=90.0)

    r = c.post(f"{BASE}/api/managed-projects/ecommerce", json={"prompt": prompt, "slug": slug})
    r.raise_for_status()
    pid = r.json()["project"]["id"]
    print("created", slug, pid)

    for _ in range(90):
        row = c.get(f"{BASE}/api/managed-projects/ecommerce/{pid}").json()
        st = row.get("status")
        if st in ("deployed", "failed"):
            print("status", st)
            if st == "failed":
                raise SystemExit(row.get("error_last"))
            break
        time.sleep(2.0)

    # Seed products via admin API
    p1 = c.post(
        f"{BASE}/api/admin/ecommerce/{slug}/products",
        json={"name": "Tee-shirt", "price_cents": 2500, "currency": "eur", "active": True, "sort": 0},
    )
    p1.raise_for_status()
    prod1 = p1.json()
    p2 = c.post(
        f"{BASE}/api/admin/ecommerce/{slug}/products",
        json={"name": "Casquette", "price_cents": 1800, "currency": "eur", "active": True, "sort": 1},
    )
    p2.raise_for_status()
    prod2 = p2.json()
    print("products", prod1.get("id"), prod2.get("id"))

    # Public list
    lp = c.get(f"{BASE}/api/public/ecommerce/{slug}/products")
    lp.raise_for_status()
    assert isinstance(lp.json(), list) and len(lp.json()) >= 2

    # Checkout
    chk = c.post(
        f"{BASE}/api/public/ecommerce/{slug}/checkout",
        json={"items": [{"product_id": prod1["id"], "qty": 1}, {"product_id": prod2["id"], "qty": 2}]},
    )
    chk.raise_for_status()
    data = chk.json()
    session_id = data["checkout_session_id"]
    order_id = data["order_id"]
    assert data.get("checkout_url")
    print("checkout", session_id, order_id)

    # Simulate webhook completion (works even without Stripe secret in dev)
    wh = c.post(
        f"{BASE}/api/public/ecommerce/{slug}/stripe/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "customer_details": {"email": "test@example.com", "name": "Test User"},
                    "shipping_details": {"address": {"country": "FR", "postal_code": "75001"}},
                }
            },
        },
    )
    wh.raise_for_status()

    # Verify status becomes paid
    st = c.get(f"{BASE}/api/public/ecommerce/{slug}/checkout/{session_id}/status")
    st.raise_for_status()
    row = st.json()
    assert row.get("status") == "paid"
    print("ok")


if __name__ == "__main__":
    main()

