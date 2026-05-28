"use client";

export type CartItem = { product_id: string; qty: number };

const KEY = "cyberforge_cart_v1";

export function getCart(): CartItem[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    const data = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(data)) return [];
    return data
      .filter((x) => x && typeof x.product_id === "string" && typeof x.qty === "number")
      .map((x) => ({ product_id: x.product_id, qty: Math.max(1, Math.min(99, x.qty)) }));
  } catch {
    return [];
  }
}

export function setCart(items: CartItem[]) {
  window.localStorage.setItem(KEY, JSON.stringify(items));
}

export function addToCart(productId: string, qty: number = 1) {
  const cart = getCart();
  const idx = cart.findIndex((c) => c.product_id === productId);
  if (idx >= 0) cart[idx] = { product_id: productId, qty: Math.min(99, cart[idx].qty + qty) };
  else cart.push({ product_id: productId, qty: Math.max(1, Math.min(99, qty)) });
  setCart(cart);
}

export function clearCart() {
  window.localStorage.removeItem(KEY);
}

