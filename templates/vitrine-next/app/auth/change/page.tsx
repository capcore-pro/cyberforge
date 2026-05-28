"use client";

import { useState } from "react";

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      const r = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const data = (await r.json()) as { ok?: boolean; message?: string };
      if (!r.ok || !data.ok) {
        setErr(data?.message || "Changement impossible.");
        return;
      }
      setMsg("Mot de passe mis à jour.");
      setCurrentPassword("");
      setNewPassword("");
    } catch {
      setErr("Erreur réseau.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-semibold">Changer le mot de passe</h1>
      <p className="mt-2 text-sm opacity-80">
        Entrez votre mot de passe actuel puis le nouveau.
      </p>

      <div className="mt-6 space-y-3 rounded-lg border border-white/10 bg-black/20 p-4">
        <label className="text-sm">Mot de passe actuel</label>
        <input
          className="w-full rounded bg-black/30 p-2 text-sm outline-none"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
        />
        <label className="text-sm">Nouveau mot de passe</label>
        <input
          className="w-full rounded bg-black/30 p-2 text-sm outline-none"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <button
          className="w-full rounded bg-white/10 px-3 py-2 text-sm hover:bg-white/15 disabled:opacity-50"
          onClick={() => void submit()}
          disabled={busy}
        >
          {busy ? "En cours…" : "Mettre à jour"}
        </button>
        {err ? <div className="text-sm text-red-300">{err}</div> : null}
        {msg ? <div className="text-sm text-green-300">{msg}</div> : null}
        <div className="text-xs opacity-80">
          <a className="underline" href="/auth">
            Retour
          </a>
        </div>
      </div>
    </div>
  );
}

