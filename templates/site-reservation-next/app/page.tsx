async function api(path: string) {
  const base = process.env.NEXT_PUBLIC_RESERVATION_API_BASE_URL || "";
  const slug = process.env.NEXT_PUBLIC_RESERVATION_SLUG || "";
  const url = `${base.replace(/\/$/, "")}/api/public/reservation/${encodeURIComponent(slug)}${path}`;
  const r = await fetch(url, { cache: "no-store" });
  return { ok: r.ok, status: r.status, body: await r.text() };
}

export default async function Page() {
  const services = await api("/services");
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>Réservation en ligne</h1>
      <div style={{ opacity: 0.8 }}>Prototype V1 (sans paiement)</div>
      <div style={{ fontSize: 14, opacity: 0.7 }}>
        Configure les services et horaires dans CyberForge, puis recharge cette page.
      </div>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          padding: 12,
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 10,
        }}
      >
        {services.body}
      </pre>
    </div>
  );
}

