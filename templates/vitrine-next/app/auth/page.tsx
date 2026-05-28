"use client";

import { useEffect, useState } from "react";

export default function AuthPage() {
  const [nextPath, setNextPath] = useState("/");

  useEffect(() => {
    try {
      const sp = new URLSearchParams(window.location.search);
      setNextPath(sp.get("next") || "/");
    } catch {
      setNextPath("/");
    }
  }, []);

  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      const r = await fetch("/api/auth/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = (await r.json()) as { ok?: boolean; message?: string };
      if (!r.ok || !data.ok) {
        setError(data?.message || "Mot de passe invalide.");
        return;
      }
      window.location.href = nextPath;
    } catch {
      setError("Erreur réseau.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-semibold">Accès protégé</h1>
      <p className="mt-2 text-sm opacity-80">
        Cette vitrine est protégée par mot de passe.
      </p>

      <div className="mt-6 space-y-3 rounded-lg border border-white/10 bg-black/20 p-4">
        <label className="text-sm">Mot de passe</label>
        <input
          className="w-full rounded bg-black/30 p-2 text-sm outline-none"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit();
          }}
        />
        <button
          className="w-full rounded bg-white/10 px-3 py-2 text-sm hover:bg-white/15 disabled:opacity-50"
          onClick={() => void submit()}
          disabled={busy}
        >
          {busy ? "Validation…" : "Entrer"}
        </button>
        {error ? <div className="text-sm text-red-300">{error}</div> : null}
        <div className="flex items-center justify-between text-xs opacity-80">
          <a className="underline" href="/auth/forgot">
            Mot de passe oublié
          </a>
          <a className="underline" href="/auth/change">
            Changer le mot de passe
          </a>
        </div>
      </div>
    </div>
  );
}

