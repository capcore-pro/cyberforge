import { useCallback, useEffect, useState } from "react";
import {
  Euro,
  Receipt,
  Repeat,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  GLASS_BTN,
  GLASS_KPI,
  GLASS_SECTION,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import { formatDateFr, formatEur } from "@/lib/accounting-export";
import { fetchCockpitDashboard } from "@/lib/cockpit-api";
import {
  fetchStripeDashboard,
  STRIPE_CAPCORE_PROJECT_ID,
  type StripeTransaction,
} from "@/lib/stripe-api";

function KpiCard({
  label,
  value,
  icon,
  valueClass = "text-white",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className={GLASS_KPI}>
      <div className="mb-3">{icon}</div>
      <p className="text-xs font-semibold uppercase tracking-widest text-white/40">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-bold tabular-nums ${valueClass}`}>
        {value}
      </p>
    </div>
  );
}

function txStatusClass(status: string): string {
  if (status === "paid") return "text-emerald-300";
  if (status === "pending") return "text-amber-300";
  if (status === "failed") return "text-red-300";
  return "text-white/45";
}

export function AccountingOverviewPanel() {
  const [loading, setLoading] = useState(true);
  const [totalCollected, setTotalCollected] = useState(0);
  const [revenueMonth, setRevenueMonth] = useState(0);
  const [mrr, setMrr] = useState(0);
  const [apiExpenses, setApiExpenses] = useState(0);
  const [recent, setRecent] = useState<StripeTransaction[]>([]);
  const [stripeAvailable, setStripeAvailable] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);

    const [stripeRes, cockpitRes] = await Promise.all([
      fetchStripeDashboard(STRIPE_CAPCORE_PROJECT_ID),
      fetchCockpitDashboard(),
    ]);

    if (!stripeRes.ok) {
      const msg = apiErrorMessage(stripeRes, "Stripe indisponible.");
      if (shouldSilenceApiError(msg)) {
        logAccountingApiError("Vue d'ensemble / Stripe", msg);
      } else {
        logAccountingApiError("Vue d'ensemble / Stripe", msg);
      }
      setStripeAvailable(false);
      setTotalCollected(0);
      setRevenueMonth(0);
      setMrr(0);
      setRecent([]);
    } else {
      setStripeAvailable(true);
      const dash = stripeRes.data;
      setTotalCollected(dash?.total_collected_eur ?? 0);
      setRevenueMonth(dash?.revenue_this_month_eur ?? 0);
      setMrr(dash?.active_subscriptions_mrr_eur ?? 0);
      setRecent((dash?.recent_transactions ?? []).slice(0, 5));
    }

    if (cockpitRes.ok && cockpitRes.data) {
      setApiExpenses(
        cockpitRes.data.spent_month_eur ??
          cockpitRes.data.expenses?.month_eur ??
          0,
      );
    } else if (!cockpitRes.ok) {
      logAccountingApiError(
        "Vue d'ensemble / Cockpit",
        apiErrorMessage(cockpitRes, "Cockpit indisponible."),
      );
      setApiExpenses(0);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const profit = revenueMonth - apiExpenses;
  const displayValue = (v: number, available = true) =>
    available ? formatEur(v) : "—";

  if (loading) {
    return (
      <p className="animate-pulse text-sm text-white/50">
        Chargement des indicateurs…
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-6">
        <div className="md:col-span-2">
          <KpiCard
            label="CA total encaissé"
            value={displayValue(totalCollected, stripeAvailable)}
            valueClass="text-emerald-300"
            icon={<Euro className="h-6 w-6 text-emerald-400/80" aria-hidden />}
          />
        </div>
        <div className="md:col-span-2">
          <KpiCard
            label="CA ce mois"
            value={displayValue(revenueMonth, stripeAvailable)}
            valueClass="text-[#d4a843]"
            icon={
              <TrendingUp className="h-6 w-6 text-[#d4a843]/80" aria-hidden />
            }
          />
        </div>
        <div className="md:col-span-2">
          <KpiCard
            label="MRR (abonnements)"
            value={displayValue(mrr, stripeAvailable)}
            valueClass="text-blue-300"
            icon={<Repeat className="h-6 w-6 text-blue-400/80" aria-hidden />}
          />
        </div>
        <div className="md:col-span-3">
          <KpiCard
            label="Dépenses API ce mois"
            value={formatEur(apiExpenses)}
            valueClass="text-red-300"
            icon={
              <TrendingDown className="h-6 w-6 text-red-400/80" aria-hidden />
            }
          />
        </div>
        <div className="md:col-span-3">
          <KpiCard
            label="Bénéfice estimé (CA − API)"
            value={displayValue(profit, stripeAvailable)}
            valueClass={profit >= 0 ? "text-emerald-300" : "text-red-300"}
            icon={<Wallet className="h-6 w-6 text-white/50" aria-hidden />}
          />
        </div>
      </div>

      <section className={GLASS_SECTION}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-white/45">
            Dernières transactions
          </h2>
          <button type="button" onClick={() => void load()} className={GLASS_BTN}>
            Actualiser
          </button>
        </div>

        {recent.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Receipt
              className="mb-3 h-10 w-10 text-white/20"
              aria-hidden
            />
            <p className="text-sm text-white/30">
              Aucune transaction pour le moment
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-widest text-white/40">
                  <th className="px-3 py-3 font-medium">Date</th>
                  <th className="px-3 py-3 font-medium">Description</th>
                  <th className="px-3 py-3 font-medium">Client</th>
                  <th className="px-3 py-3 text-right font-medium">Montant</th>
                  <th className="px-3 py-3 font-medium">Statut</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-white/5 transition hover:bg-white/5"
                  >
                    <td className="px-3 py-3 text-white/50">
                      {formatDateFr(tx.created_at)}
                    </td>
                    <td className="px-3 py-3 text-white">
                      {tx.description ?? "Paiement Stripe"}
                    </td>
                    <td className="px-3 py-3 text-white/50">
                      {tx.customer_email ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-right font-medium text-[#d4a843]">
                      {formatEur(tx.amount_eur)}
                    </td>
                    <td
                      className={`px-3 py-3 text-xs uppercase ${txStatusClass(tx.status)}`}
                    >
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
