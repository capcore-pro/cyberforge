"use client";

import { useEffect, useMemo, useState } from "react";
import { clearCart, getCart, setCart, type CartItem } from "./cart-store";

type Product = { id: string; name: string; price_cents: number; currency: string };

async function fetchProducts(): Promise<Product[]> {
  const base = process.env.NEXT_PUBLIC_ECOMMERCE_API_BASE_URL || "";
  const slug = process.env.NEXT_PUBLIC_ECOMMERCE_SLUG || "";
  const url = `${base.replace(/\/$/, "")}/api/public/ecommerce/${encodeURIComponent(slug)}/products`;
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) return [];
  const data = await r.json();
  return Array.isArray(data) ? (data as Product[]) : [];
}

async function createCheckout(items: CartItem[]) {
  const base = process.env.NEXT_PUBLIC_ECOMMERCE_API_BASE_URL || "";
  const slug = process.env.NEXT_PUBLIC_ECOMMERCE_SLUG || "";
  const url = `${base.replace(/\/$/, "")}/api/public/ecommerce/${encodeURIComponent(slug)}/checkout`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

function euros(cents: number) {
  return (cents / 100).toFixed(2).replace(".", ",") + " €";
}

export default function CartPage() {
  const [cart, setCartState] = useState<CartItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setCartState(getCart());
    void fetchProducts().then(setProducts);
  }, []);

  const byId = useMemo(() => new Map(products.map((p) => [p.id, p])), [products]);

  const subtotal = useMemo(() => {
    let s = 0;
    for (const it of cart) {
      const p = byId.get(it.product_id);
      if (p) s += p.price_cents * it.qty;
    }
    return s;
  }, [cart, byId]);

  function changeQty(productId: string, qty: number) {
    const next = cart
      .map((c) => (c.product_id === productId ? { ...c, qty } : c))
      .filter((c) => c.qty > 0);
    setCart(next);
    setCartState(next);
  }

  async function onCheckout() {
    setErr(null);
    if (!cart.length) return;
    setBusy(true);
    try {
      const resp = await createCheckout(cart);
      clearCart();
      window.location.href = resp.checkout_url;
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>Panier</h1>
      {cart.length === 0 ? <div style={{ opacity: 0.8 }}>Panier vide.</div> : null}
      {cart.map((it) => {
        const p = byId.get(it.product_id);
        if (!p) return null;
        return (
          <div
            key={it.product_id}
            style={{
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 10,
              padding: 12,
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{p.name}</div>
              <div style={{ fontSize: 13, opacity: 0.7 }}>{euros(p.price_cents)} / unité</div>
            </div>
            <input
              type="number"
              min={0}
              max={99}
              value={it.qty}
              onChange={(e) => changeQty(it.product_id, Math.max(0, Math.min(99, Number(e.target.value))))}
              style={{ width: 80, background: "rgba(255,255,255,0.06)", color: "#e5e7eb", borderRadius: 8, border: 0, padding: 8 }}
            />
          </div>
        );
      })}
      <div style={{ display: "flex", justifyContent: "space-between", opacity: 0.9 }}>
        <div>Sous-total</div>
        <div>{euros(subtotal)}</div>
      </div>
      <button
        disabled={busy || cart.length === 0}
        onClick={() => void onCheckout()}
        style={{
          border: 0,
          borderRadius: 10,
          padding: "12px 14px",
          background: busy ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.16)",
          color: "#e5e7eb",
          cursor: "pointer",
        }}
      >
        {busy ? "Redirection…" : "Payer (Stripe Checkout)"}
      </button>
      {err ? <div style={{ color: "#fca5a5", fontSize: 13 }}>{err}</div> : null}
      <div style={{ fontSize: 12, opacity: 0.6 }}>
        Paiement en mode test. Les frais de livraison sont ajoutés côté serveur.
      </div>
    </div>
  );
}

