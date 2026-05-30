import { useCallback, useEffect, useState } from "react";
import { SecureKeyInput } from "@/components/SecureKeyInput";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  applyClientStripe,
  fetchClientStripe,
  saveClientStripe,
} from "@/lib/stripe-api";
import type { UnifiedProject } from "@/lib/unified-projects";

export function projectSupportsClientStripe(project: UnifiedProject): boolean {
  return project.type === "ecommerce" || project.type === "reservation";
}

export function ProjectClientStripeSection({
  project,
  onConfiguredChange,
}: {
  project: UnifiedProject;
  onConfiguredChange?: (configured: boolean) => void;
}) {
  const managedId = project.managedId;
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [secretKey, setSecretKey] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!managedId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    const res = await fetchClientStripe(managedId);
    setLoading(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de charger la config Stripe client."));
      return;
    }
    setConfigured(Boolean(res.data?.configured));
    onConfiguredChange?.(Boolean(res.data?.configured));
  }, [managedId, onConfiguredChange]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!projectSupportsClientStripe(project) || !managedId) {
    return null;
  }

  async function handleApply() {
    if (!managedId) return;
    setBusy(true);
    setError(null);
    setToast(null);

    if (secretKey.trim()) {
      const saveRes = await saveClientStripe(managedId, {
        secret_key: secretKey.trim(),
        webhook_secret: webhookSecret.trim() || null,
        project_name: project.name,
      });
      if (!saveRes.ok) {
        setBusy(false);
        setError(apiErrorMessage(saveRes, "Enregistrement des clés impossible."));
        return;
      }
      setConfigured(true);
      onConfiguredChange?.(true);
    } else if (!configured) {
      setBusy(false);
      setError("Renseignez la clé secrète Stripe du client.");
      return;
    }

    const applyRes = await applyClientStripe(managedId);
    setBusy(false);
    if (!applyRes.ok) {
      setError(apiErrorMessage(applyRes, "Application impossible."));
      return;
    }
    setToast(applyRes.data?.message ?? "Paiement client activé.");
    setSecretKey("");
    await load();
    window.setTimeout(() => setToast(null), 4000);
  }

  return (
    <div className="space-y-4 rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium text-cf-text">Paiement client</p>
        {loading ? (
          <span className="text-[10px] text-cf-muted">…</span>
        ) : (
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
              configured
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-amber-500/40 bg-amber-500/10 text-amber-200"
            }`}
          >
            {configured ? "Paiement actif" : "Paiement non configuré"}
          </span>
        )}
      </div>

      <p className="text-[11px] leading-relaxed text-cf-muted">
        Demandez à votre client sa clé Stripe secrète sur{" "}
        <a
          href="https://dashboard.stripe.com/apikeys"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cf-info hover:underline"
        >
          stripe.com/dashboard → Développeurs → Clés API
        </a>
        . Les paiements du site e-commerce / réservation seront encaissés sur son compte.
      </p>

      <SecureKeyInput
        label="Clé Stripe du client (STRIPE_SECRET_KEY)"
        value={secretKey}
        onChange={setSecretKey}
        placeholder={configured ? "Laisser vide pour conserver la clé actuelle" : "sk_live_…"}
        disabled={busy}
      />

      <SecureKeyInput
        label="Webhook secret client"
        value={webhookSecret}
        onChange={setWebhookSecret}
        placeholder="whsec_…"
        disabled={busy}
      />

      {error ? <p className="text-xs text-red-300">{error}</p> : null}
      {toast ? (
        <p className="text-xs text-emerald-300">{toast}</p>
      ) : null}

      <button
        type="button"
        disabled={busy || loading}
        onClick={() => void handleApply()}
        className="rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-xs text-cf-gold hover:border-cf-gold disabled:opacity-50"
      >
        {busy ? "Application…" : "Appliquer"}
      </button>
    </div>
  );
}
