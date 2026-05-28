"use client";

import { useEffect, useState } from "react";

async function status(sessionId: string) {
  const base = process.env.NEXT_PUBLIC_ECOMMERCE_API_BASE_URL || "";
  const slug = process.env.NEXT_PUBLIC_ECOMMERCE_SLUG || "";
  const url = `${base.replace(/\/$/, "")}/api/public/ecommerce/${encodeURIComponent(slug)}/checkout/${encodeURIComponent(sessionId)}/status`;
  const r = await fetch(url, { cache: "no-store" });
  const text = await r.text();
  try {
    return { ok: r.ok, data: JSON.parse(text) };
  } catch {
    return { ok: r.ok, data: text };
  }
}

export default function SuccessPage() {
  const [state, setState] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const sessionId = p.get("session_id");
    if (!sessionId) return;
    let cancelled = false;
    const tick = async () => {
      const s = await status(sessionId);
      if (cancelled) return;
      if (!s.ok) setErr(JSON.stringify(s.data));
      else setState(s.data);
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h1 style={{ margin: 0 }}>Merci</h1>
      <div style={{ opacity: 0.8 }}>Confirmation de commande</div>
      {err ? <div style={{ color: "#fca5a5", fontSize: 13 }}>{err}</div> : null}
      <pre style={{ padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, whiteSpace: "pre-wrap" }}>
        {state ? JSON.stringify(state, null, 2) : "Chargement…"}
      </pre>
      <a href="/" style={{ color: "#e5e7eb" }}>
        Retour au catalogue
      </a>
    </div>
  );
}

