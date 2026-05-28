async function api(path: string) {
  const base = process.env.NEXT_PUBLIC_ECOMMERCE_API_BASE_URL || "";
  const slug = process.env.NEXT_PUBLIC_ECOMMERCE_SLUG || "";
  const url = `${base.replace(/\/$/, "")}/api/public/ecommerce/${encodeURIComponent(slug)}${path}`;
  const r = await fetch(url, { cache: "no-store" });
  return { ok: r.ok, status: r.status, body: await r.text() };
}

export default async function Page() {
  const products = await api("/products");
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>Catalogue</h1>
      <div style={{ opacity: 0.8 }}>Prototype V1 (Stripe Checkout)</div>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          padding: 12,
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 10,
        }}
      >
        {products.body}
      </pre>
      <div style={{ fontSize: 14, opacity: 0.7 }}>
        Ajoute des produits depuis CyberForge (Admin catalogue), puis recharge.
      </div>
    </div>
  );
}

