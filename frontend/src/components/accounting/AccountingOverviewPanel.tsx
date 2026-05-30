import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import { formatDateFr, formatEur } from "@/lib/accounting-export";
import { fetchCockpitDashboard } from "@/lib/cockpit-api";
import { fetchStripeDashboard, STRIPE_CAPCORE_PROJECT_ID, type StripeTransaction } from "@/lib/stripe-api";

function MetricCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-card border p-5 shadow-card ${
        accent
          ? "border-cf-gold/40 bg-cf-active"
          : "border-cf-border-input bg-cf-card"
      }`}
    >
      <p className="cf-section-label mb-2">{label}</p>
      <p className={`text-2xl font-semibold ${accent ? "text-cf-gold" : "text-cf-text"}`}>
        {value}
      </p>
    </div>
  );
}

function txStatusClass(status: string): string {
  if (status === "paid") return "text-emerald-400";
  if (status === "pending") return "text-amber-300";
  if (status === "failed") return "text-red-300";
  return "text-cf-muted";
}

export function AccountingOverviewPanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCollected, setTotalCollected] = useState(0);
  const [revenueMonth, setRevenueMonth] = useState(0);
  const [mrr, setMrr] = useState(0);
  const [apiExpenses, setApiExpenses] = useState(0);
  const [recent, setRecent] = useState<StripeTransaction[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const offline = "Backend injoignable — vérifiez que l'API tourne.";

    const [stripeRes, cockpitRes] = await Promise.all([
      fetchStripeDashboard(STRIPE_CAPCORE_PROJECT_ID),
      fetchCockpitDashboard(),
    ]);

    setLoading(false);

    if (!stripeRes.ok) {
      setError(apiErrorMessage(stripeRes, offline));
      return;
    }

    const dash = stripeRes.data;
    setTotalCollected(dash?.total_collected_eur ?? 0);
    setRevenueMonth(dash?.revenue_this_month_eur ?? 0);
    setMrr(dash?.active_subscriptions_mrr_eur ?? 0);
    setRecent((dash?.recent_transactions ?? []).slice(0, 5));

    if (cockpitRes.ok && cockpitRes.data) {
      setApiExpenses(
        cockpitRes.data.spent_month_eur ?? cockpitRes.data.expenses?.month_eur ?? 0,
      );
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const profit = revenueMonth - apiExpenses;

  if (loading) {
    return <p className="animate-pulse text-sm text-cf-muted">Chargement des indicateurs…</p>;
  }

  return (
    <div className="space-y-8">
      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="CA total encaissé" value={formatEur(totalCollected)} />
        <MetricCard label="CA ce mois" value={formatEur(revenueMonth)} accent />
        <MetricCard label="MRR (abonnements)" value={formatEur(mrr)} />
        <MetricCard label="Dépenses API ce mois" value={formatEur(apiExpenses)} />
        <MetricCard
          label="Bénéfice estimé (CA − API)"
          value={formatEur(profit)}
          accent={profit >= 0}
        />
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-cf-text">Dernières transactions</h2>
          <button
            type="button"
            onClick={() => void load()}
            className="text-xs text-cf-muted hover:text-cf-gold"
          >
            Actualiser
          </button>
        </div>

        {recent.length === 0 ? (
          <p className="text-sm text-cf-muted">Aucune transaction récente.</p>
        ) : (
          <div className="overflow-x-auto rounded-card border border-cf-border-input">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-cf-border-input text-left text-[11px] uppercase tracking-wide text-cf-muted">
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 font-medium">Client</th>
                  <th className="px-4 py-3 font-medium text-right">Montant</th>
                  <th className="px-4 py-3 font-medium">Statut</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-cf-border-input/60 last:border-0"
                  >
                    <td className="px-4 py-3 text-cf-muted">{formatDateFr(tx.created_at)}</td>
                    <td className="px-4 py-3 text-cf-text">
                      {tx.description ?? "Paiement Stripe"}
                    </td>
                    <td className="px-4 py-3 text-cf-muted">{tx.customer_email ?? "—"}</td>
                    <td className="px-4 py-3 text-right font-medium text-cf-gold">
                      {formatEur(tx.amount_eur)}
                    </td>
                    <td className={`px-4 py-3 text-xs uppercase ${txStatusClass(tx.status)}`}>
                      {tx.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
