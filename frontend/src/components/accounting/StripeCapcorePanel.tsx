import { useCallback, useEffect, useMemo, useState } from "react";
import { CreditCard } from "lucide-react";
import { SecureKeyInput } from "@/components/SecureKeyInput";
import {
  GLASS_BTN,
  GLASS_KPI,
  GLASS_SECTION,
  GOLD_BTN,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
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

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
  }).format(value);
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
    <div className={GLASS_KPI}>
      <p className="text-xs font-semibold uppercase tracking-widest text-white/40">
        {label}
      </p>
      <p
        className={`mt-2 text-2xl font-bold tabular-nums ${
          accent ? "text-[#d4a843]" : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

export function StripeCapcorePanel() {
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [dashboard, setDashboard] = useState<StripeDashboard | null>(null);
  const [transactions, setTransactions] = useState<StripeTransaction[]>([]);

  const [setupOpen, setSetupOpen] = useState(false);
  const [secretKey, setSecretKey] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const statusRes = await fetchCapcoreStripe();
    if (!statusRes.ok) {
      const msg = apiErrorMessage(statusRes, "Stripe CapCore indisponible.");
      logAccountingApiError("Mes revenus / statut", msg);
      setConfigured(false);
      setDashboard(null);
      setTransactions([]);
      setLoading(false);
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
      const msg = apiErrorMessage(dashRes, "Dashboard CapCore indisponible.");
      logAccountingApiError("Mes revenus / dashboard", msg);
      setDashboard(null);
      setTransactions([]);
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
      const msg = apiErrorMessage(res, "Enregistrement impossible.");
      if (shouldSilenceApiError(msg)) {
        logAccountingApiError("Mes revenus / save", msg);
      } else {
        setSaveError(msg);
      }
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
        <h2 className="text-lg font-semibold text-white">
          Mes revenus — Stripe CapCore
        </h2>
        <p className="mt-1 text-sm text-white/50">
          Compte Stripe de Mat / CapCore pour vos propres encaissements.
          Distinct du Stripe de vos clients e-commerce.
        </p>
      </header>

      {loading ? (
        <p className="animate-pulse text-sm text-white/50">Chargement…</p>
      ) : !configured ? (
        <div className={`${GLASS_SECTION} text-center`}>
          <CreditCard
            className="mx-auto mb-4 h-12 w-12 text-[#d4a843]/70"
            aria-hidden
          />
          <p className="text-sm font-medium text-white">
            Stripe non configuré
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-white/50">
            Ajoutez votre clé secrète Stripe (compte CapCore) pour suivre vos
            revenus dans cette interface.
          </p>
          {!setupOpen ? (
            <button
              type="button"
              className={`${GOLD_BTN} mt-6`}
              onClick={() => setSetupOpen(true)}
            >
              Ajouter ma clé Stripe
            </button>
          ) : (
            <div className="mx-auto mt-6 max-w-lg space-y-4 text-left">
              <SecureKeyInput
                label="STRIPE_SECRET_KEY (CapCore)"
                value={secretKey}
                onChange={setSecretKey}
                placeholder="sk_live_… ou sk_test_…"
              />
              {saveError ? (
                <p className="text-xs text-red-300">{saveError}</p>
              ) : null}
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  type="button"
                  className={GLASS_BTN}
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
                  className={GOLD_BTN}
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

          <div className={GLASS_SECTION}>
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
              Transactions CapCore
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs uppercase tracking-widest text-white/40">
                    <th className="px-3 py-3 font-medium">Client</th>
                    <th className="px-3 py-3 text-right font-medium">Montant</th>
                    <th className="px-3 py-3 font-medium">Statut</th>
                    <th className="px-3 py-3 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.length === 0 ? (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-3 py-10 text-center text-white/30"
                      >
                        Aucune transaction pour l&apos;instant.
                      </td>
                    </tr>
                  ) : (
                    transactions.slice(0, 30).map((tx) => (
                      <tr
                        key={tx.id}
                        className="border-b border-white/5 transition hover:bg-white/5"
                      >
                        <td className="px-3 py-3 text-white">
                          {tx.customer_email || "—"}
                        </td>
                        <td className="px-3 py-3 text-right font-medium tabular-nums text-emerald-300">
                          {formatEur(Number(tx.amount_eur))}
                        </td>
                        <td className="px-3 py-3 capitalize text-white/50">
                          {tx.status}
                        </td>
                        <td className="px-3 py-3 text-white/50">
                          {formatDate(tx.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <details className={GLASS_SECTION}>
            <summary className="cursor-pointer text-sm font-medium text-white/80">
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
                className={GOLD_BTN}
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
