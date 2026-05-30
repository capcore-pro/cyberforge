import { useCallback, useEffect, useMemo, useState } from "react";
import { SecureKeyInput } from "@/components/SecureKeyInput";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchCapcoreStripe,
  fetchStripeDashboard,
  fetchStripeTransactions,
  saveCapcoreStripe,
  STRIPE_CAPCORE_PROJECT_ID,
  type StripeDashboard,
  type StripeTransaction,
} from "@/lib/stripe-api";

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

function formatEur(value: number): string {
  return eurFmt.format(value);
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-card border p-4 ${
        accent
          ? "border-cf-gold/40 bg-cf-active"
          : "border-cf-border-input bg-cf-card"
      }`}
    >
      <p className="text-[10px] font-bold uppercase tracking-wider text-cf-muted">
        {label}
      </p>
      <p
        className={`mt-2 text-2xl font-bold tabular-nums ${
          accent ? "text-cf-gold" : "text-cf-text"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

/**
 * Mes revenus CapCore — clé Stripe Mat + dashboard transactions.
 */
export function StripeCapcorePanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configured, setConfigured] = useState(false);
  const [dashboard, setDashboard] = useState<StripeDashboard | null>(null);
  const [transactions, setTransactions] = useState<StripeTransaction[]>([]);

  const [setupOpen, setSetupOpen] = useState(false);
  const [secretKey, setSecretKey] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const statusRes = await fetchCapcoreStripe();
    if (!statusRes.ok) {
      setLoading(false);
      setError(apiErrorMessage(statusRes, "Impossible de charger Stripe CapCore."));
      return;
    }
    const isConfigured = Boolean(statusRes.data?.configured);
    setConfigured(isConfigured);

    if (!isConfigured) {
      setDashboard(null);
      setTransactions([]);
      setLoading(false);
      return;
    }

    const [dashRes, txRes] = await Promise.all([
      fetchStripeDashboard(STRIPE_CAPCORE_PROJECT_ID),
      fetchStripeTransactions({
        project_id: STRIPE_CAPCORE_PROJECT_ID,
        status: "paid",
        limit: 100,
      }),
    ]);
    setLoading(false);

    if (!dashRes.ok) {
      setError(apiErrorMessage(dashRes, "Dashboard CapCore indisponible."));
      return;
    }
    setDashboard(dashRes.data);
    setTransactions(txRes.ok && Array.isArray(txRes.data) ? txRes.data : []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const monthTotal = useMemo(() => {
    if (dashboard) return dashboard.revenue_this_month_eur;
    const now = new Date();
    const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    return transactions
      .filter((tx) => tx.status === "paid" && tx.created_at.startsWith(key))
      .reduce((sum, tx) => sum + Number(tx.amount_eur || 0), 0);
  }, [dashboard, transactions]);

  async function handleSaveKey() {
    if (!secretKey.trim()) return;
    setSaveBusy(true);
    setSaveError(null);
    const res = await saveCapcoreStripe({ secret_key: secretKey.trim() });
    setSaveBusy(false);
    if (!res.ok) {
      setSaveError(apiErrorMessage(res, "Enregistrement impossible."));
      return;
    }
    setSecretKey("");
    setSetupOpen(false);
    setConfigured(true);
    await load();
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-cf-text">
          Mes revenus — Stripe CapCore
        </h2>
        <p className="mt-1 text-sm text-cf-muted">
          Compte Stripe de Mat / CapCore pour vos propres encaissements (abonnements,
          factures, apps desktop). Distinct du Stripe de vos clients e-commerce.
        </p>
      </header>

      {error ? (
        <p className="rounded-card border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
      ) : !configured ? (
        <div className="rounded-card border border-amber-500/30 bg-amber-950/20 p-6">
          <p className="text-sm font-medium text-amber-100">
            Stripe CapCore non configuré
          </p>
          <p className="mt-2 text-sm text-cf-muted">
            Ajoutez votre clé secrète Stripe (compte CapCore) pour suivre vos revenus
            dans cette interface.
          </p>
          {!setupOpen ? (
            <button
              type="button"
              className="mt-4 rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm text-cf-gold hover:border-cf-gold"
              onClick={() => setSetupOpen(true)}
            >
              Ajouter ma clé Stripe
            </button>
          ) : (
            <div className="mt-4 max-w-lg space-y-4">
              <SecureKeyInput
                label="STRIPE_SECRET_KEY (CapCore)"
                value={secretKey}
                onChange={setSecretKey}
                placeholder="sk_live_… ou sk_test_…"
              />
              {saveError ? (
                <p className="text-xs text-red-300">{saveError}</p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-control border border-cf-border-input px-4 py-2 text-sm text-cf-muted"
                  onClick={() => {
                    setSetupOpen(false);
                    setSecretKey("");
                    setSaveError(null);
                  }}
                >
                  Annuler
                </button>
                <button
                  type="button"
                  disabled={saveBusy || !secretKey.trim()}
                  className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm text-cf-gold disabled:opacity-50"
                  onClick={() => void handleSaveKey()}
                >
                  {saveBusy ? "Enregistrement…" : "Enregistrer la clé"}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="CA total (CapCore)"
              value={formatEur(dashboard?.total_collected_eur ?? 0)}
              accent
            />
            <MetricCard
              label="CA ce mois"
              value={formatEur(monthTotal)}
              accent
            />
            <MetricCard
              label="Transactions enregistrées"
              value={String(transactions.length)}
            />
          </div>

          <div className="overflow-hidden rounded-card border border-cf-border-input">
            <div className="border-b border-cf-border-input bg-cf-secondary/40 px-4 py-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-cf-muted">
                Transactions CapCore
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-xs">
                <thead>
                  <tr className="border-b border-cf-border-input text-[10px] uppercase tracking-wider text-cf-muted">
                    <th className="px-3 py-2">Client</th>
                    <th className="px-3 py-2 text-right">Montant</th>
                    <th className="px-3 py-2">Statut</th>
                    <th className="px-3 py-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-3 py-8 text-center text-cf-muted">
                        Aucune transaction pour l&apos;instant.
                      </td>
                    </tr>
                  ) : (
                    transactions.slice(0, 30).map((tx) => (
                      <tr
                        key={tx.id}
                        className="border-b border-cf-border-input/60 hover:bg-cf-active/5"
                      >
                        <td className="px-3 py-2 text-cf-text">
                          {tx.customer_email || "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-medium tabular-nums text-emerald-400">
                          {formatEur(Number(tx.amount_eur))}
                        </td>
                        <td className="px-3 py-2 capitalize text-cf-muted">{tx.status}</td>
                        <td className="px-3 py-2 text-cf-muted">
                          {formatDate(tx.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <details className="rounded-card border border-cf-border-input bg-cf-card p-4">
            <summary className="cursor-pointer text-sm font-medium text-cf-text">
              Modifier la clé Stripe CapCore
            </summary>
            <div className="mt-4 max-w-lg space-y-3">
              <SecureKeyInput
                label="Nouvelle STRIPE_SECRET_KEY"
                value={secretKey}
                onChange={setSecretKey}
                placeholder="sk_live_…"
              />
              {saveError ? (
                <p className="text-xs text-red-300">{saveError}</p>
              ) : null}
              <button
                type="button"
                disabled={saveBusy || !secretKey.trim()}
                className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-xs text-cf-gold disabled:opacity-50"
                onClick={() => void handleSaveKey()}
              >
                {saveBusy ? "Mise à jour…" : "Mettre à jour la clé"}
              </button>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
