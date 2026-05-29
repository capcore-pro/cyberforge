import { useCallback, useEffect, useState } from "react";
import type { ArchitectPlanCosts } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import { fetchProjectCosts, resetProjectCosts } from "@/lib/costs-api";

export interface PricingLiveData {
  architectPlan: ArchitectPlanCosts | null;
  totalEur: number;
  byService: Record<string, number>;
  marginMultiplier: number | null;
  updatedAt?: string | null;
}

export interface PricingWidgetProps {
  mode: "live" | "static";
  projectId: string;
  /** Mode live — données mises à jour par le parent (SSE + polling) */
  liveData?: PricingLiveData | null;
  className?: string;
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: value > 0 && value < 0.01 ? 4 : 2,
    maximumFractionDigits: value > 0 && value < 0.01 ? 4 : 2,
  }).format(value);
}

function formatEurRange(min: number, max: number): string {
  return `${formatEur(min)} – ${formatEur(max)}`;
}

function formatMultiplier(value: number): string {
  return `×${new Intl.NumberFormat("fr-FR").format(value)}`;
}

function complexityBarColor(score: number): string {
  if (score <= 3) return "bg-emerald-500";
  if (score <= 6) return "bg-amber-500";
  return "bg-red-500";
}

function complexityTextColor(score: number): string {
  if (score <= 3) return "text-emerald-400";
  if (score <= 6) return "text-amber-400";
  return "text-red-400";
}

function ProgressBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-cyber-bg/80 ring-1 ring-cyber-border/60"
      role="progressbar"
      aria-valuenow={score}
      aria-valuemin={0}
      aria-valuemax={10}
      aria-label={`Complexité ${score} sur 10`}
    >
      <div
        className={`h-full rounded-full transition-all duration-500 ease-out ${complexityBarColor(score)}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function PricingBody({
  architectPlan,
  totalEur,
  marginMultiplier,
  apiCostPulse,
}: {
  architectPlan: ArchitectPlanCosts;
  totalEur: number;
  marginMultiplier: number | null;
  apiCostPulse?: boolean;
}) {
  const score = architectPlan.complexity_score;

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyber-muted">
            Complexité
          </span>
          <span
            className={`text-xs font-semibold ${complexityTextColor(score)}`}
          >
            {architectPlan.complexity_label}{" "}
            <span className="font-mono text-cyber-text">
              {score}/10
            </span>
          </span>
        </div>
        <ProgressBar score={score} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-cyber-border/80 bg-cyber-bg/50 px-3 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
            Valeur marché humain
          </p>
          <p className="mt-1 font-mono text-sm text-cyber-text">
            {formatEurRange(
              architectPlan.market_price_min,
              architectPlan.market_price_max,
            )}
          </p>
        </div>

        <div className="rounded-lg border border-cyber-accent/35 bg-cyber-accent/5 px-3 py-2.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyber-violet">
            Ton prix suggéré
          </p>
          <p className="mt-1 font-mono text-lg font-semibold text-cyber-neon">
            {formatEurRange(
              architectPlan.suggested_price_min,
              architectPlan.suggested_price_max,
            )}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3 border-t border-cyber-border/60 pt-3">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
            Coût API
          </p>
          <p
            className={`mt-0.5 font-mono text-xs text-cyber-muted transition-colors ${
              apiCostPulse ? "text-cyber-violet" : ""
            }`}
          >
            {formatEur(totalEur)}
          </p>
        </div>
        {marginMultiplier != null && marginMultiplier > 0 ? (
          <span
            className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 font-mono text-sm font-bold text-emerald-400"
            title="Prix suggéré bas / coût API"
          >
            {formatMultiplier(marginMultiplier)}
          </span>
        ) : (
          <span className="text-[10px] text-cyber-muted">Marge —</span>
        )}
      </div>
    </div>
  );
}

/**
 * Tarification ArchitectAI + coûts API — mode live (génération) ou static (fiche projet).
 */
export function PricingWidget({
  mode,
  projectId,
  liveData,
  className = "",
}: PricingWidgetProps) {
  const [staticData, setStaticData] = useState<PricingLiveData | null>(null);
  const [loading, setLoading] = useState(mode === "static");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [prevTotal, setPrevTotal] = useState<number | null>(null);
  const [apiCostPulse, setApiCostPulse] = useState(false);

  const loadStatic = useCallback(async () => {
    if (!projectId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetchProjectCosts(projectId);
      if (!response.ok || !response.data) {
        setError(
          apiErrorMessage(response, "Impossible de charger les coûts du projet."),
        );
        return;
      }
      const d = response.data;
      setStaticData({
        architectPlan: d.architect_plan,
        totalEur: d.total_eur,
        byService: d.by_service,
        marginMultiplier: d.margin_multiplier,
        updatedAt: d.updated_at,
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erreur lors du chargement des coûts.",
      );
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (mode !== "static") return;
    void loadStatic();
  }, [mode, loadStatic]);

  const data = mode === "live" ? liveData : staticData;

  useEffect(() => {
    if (mode !== "live" || !data) return;
    if (prevTotal !== null && data.totalEur !== prevTotal) {
      setApiCostPulse(true);
      const t = window.setTimeout(() => setApiCostPulse(false), 600);
      return () => window.clearTimeout(t);
    }
    setPrevTotal(data.totalEur);
  }, [mode, data?.totalEur, prevTotal, data]);

  async function handleRecalculate() {
    if (!projectId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const reset = await resetProjectCosts(projectId);
      if (!reset.ok) {
        setError(apiErrorMessage(reset, "Impossible de réinitialiser les coûts."));
        return;
      }
      await loadStatic();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erreur lors du recalcul.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (mode === "live" && !data?.architectPlan) {
    return null;
  }

  if (mode === "static" && loading && !staticData) {
    return (
      <section
        className={`rounded-xl border border-cyber-border/80 bg-cyber-surface/90 p-4 ${className}`}
        aria-label="Tarification"
      >
        <p className="text-xs text-cyber-muted animate-pulse">Chargement des coûts…</p>
      </section>
    );
  }

  if (mode === "static" && !loading && !data?.architectPlan && !error) {
    return (
      <section
        className={`rounded-xl border border-cyber-border/80 bg-cyber-surface/90 p-4 ${className}`}
        aria-label="Tarification"
      >
        <p className="text-xs text-cyber-muted">
          Aucune analyse ArchitectAI enregistrée pour ce projet.
        </p>
        <button
          type="button"
          className="cyber-action-btn mt-3 text-[11px]"
          disabled={busy}
          onClick={() => void loadStatic()}
        >
          Actualiser
        </button>
      </section>
    );
  }

  if (!data?.architectPlan) {
    if (error) {
      return (
        <section
          className={`rounded-xl border border-red-400/30 bg-red-950/20 p-4 ${className}`}
        >
          <p className="text-xs text-red-300">{error}</p>
        </section>
      );
    }
    return null;
  }

  return (
    <section
      className={`rounded-xl border border-cyber-border/80 bg-gradient-to-br from-cyber-surface/95 to-cyber-bg/90 p-4 shadow-inner ${className}`}
      aria-label="Tarification et coûts API"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
          {mode === "live" ? "Tarification · live" : "Tarification"}
        </h3>
        {mode === "static" ? (
          <button
            type="button"
            className="rounded border border-cyber-border px-2 py-1 text-[10px] text-cyber-accent hover:border-cyber-violet disabled:opacity-50"
            disabled={busy || loading}
            onClick={() => void handleRecalculate()}
          >
            {busy ? "…" : "Recalculer"}
          </button>
        ) : null}
      </div>

      {error ? (
        <p className="mb-3 rounded border border-red-400/30 bg-red-400/10 px-2 py-1 text-[11px] text-red-300">
          {error}
        </p>
      ) : null}

      <PricingBody
        architectPlan={data.architectPlan}
        totalEur={data.totalEur}
        marginMultiplier={data.marginMultiplier}
        apiCostPulse={mode === "live" && apiCostPulse}
      />

      {mode === "static" && data.updatedAt ? (
        <p className="mt-3 text-[10px] text-cyber-muted">
          Mis à jour{" "}
          {new Intl.DateTimeFormat("fr-FR", {
            dateStyle: "short",
            timeStyle: "short",
          }).format(new Date(data.updatedAt))}
        </p>
      ) : null}
    </section>
  );
}
