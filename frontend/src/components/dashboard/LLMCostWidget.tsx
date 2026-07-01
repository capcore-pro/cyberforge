import type { LLMStats } from "@/lib/dashboard-api";
import { USD_TO_EUR } from "@/lib/dashboard-api";

interface LLMCostWidgetProps {
  data: LLMStats | null;
  loading?: boolean;
}

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12]";

const eurPreciseFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatEurFromUsd(usd: number): string {
  return eurPreciseFmt.format(usd * USD_TO_EUR);
}

function formatProviderLabel(provider: string): string {
  const key = provider.toLowerCase();
  if (key === "mistral") return "Mistral";
  if (key === "gemini") return "Gemini Flash";
  if (key.includes("mistral") && key.includes("small")) return "Mistral Small";
  if (key.includes("mistral") && key.includes("large")) return "Mistral Large";
  return provider
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const PROVIDER_BAR_COLORS = ["bg-cf-cyan", "bg-[#f59e0b]", "bg-cf-purple"];

function providerBarColor(index: number): string {
  return PROVIDER_BAR_COLORS[index % PROVIDER_BAR_COLORS.length];
}

function SkeletonBars() {
  return (
    <div className="space-y-4" aria-hidden>
      {[0, 1, 2].map((i) => (
        <div key={i} className="space-y-1.5 animate-pulse">
          <div className="flex justify-between gap-3">
            <div className="h-3 w-24 rounded bg-white/10" />
            <div className="h-3 w-12 rounded bg-white/10" />
          </div>
          <div className="h-2 w-full rounded-full bg-white/10" />
        </div>
      ))}
    </div>
  );
}

export function LLMCostWidget({ data, loading }: LLMCostWidgetProps) {
  const monthly = data?.monthly;
  const totalUsd = monthly?.total_cost_usd ?? 0;
  const totalTokens = monthly?.total_tokens ?? 0;
  const hasData = totalUsd > 0 || totalTokens > 0;

  const agents = [...(monthly?.by_agent ?? [])]
    .sort((a, b) => b.cost_usd - a.cost_usd)
    .slice(0, 5);
  const providers = [...(monthly?.by_provider ?? [])]
    .filter(
      (row) =>
        row.provider.toLowerCase() === "mistral" ||
        row.provider.toLowerCase() === "gemini" ||
        row.cost_usd > 0,
    )
    .sort((a, b) => b.cost_usd - a.cost_usd);
  const maxAgentCost = agents.length > 0 ? agents[0].cost_usd : 0;
  const maxProviderCost =
    providers.length > 0 ? providers[0].cost_usd : 0;

  const agentBarColors = ["bg-cf-cyan", "bg-[#f59e0b]", "bg-cf-purple"];

  return (
    <div className={`${V2_CARD} p-5`}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-mono text-xs tracking-wide text-cf-cyan">
          // coût LLM ce mois
        </h2>
        <span className="rounded-full border border-cf-cyan/30 bg-cf-cyan/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-cf-cyan">
          Données réelles
        </span>
      </div>

      {loading ? (
        <SkeletonBars />
      ) : !hasData ? (
        <p className="text-sm text-cf-muted">
          Aucune génération ce mois — données disponibles après la première
          génération
        </p>
      ) : (
        <>
          <p className="font-mono text-3xl font-semibold tabular-nums text-cf-text">
            {formatEurFromUsd(totalUsd)}
          </p>
          <p className="mt-1 font-mono text-sm text-cf-muted">
            {totalTokens.toLocaleString("fr-FR")} tokens
          </p>

          {agents.length > 0 ? (
            <div className="mt-5 space-y-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cf-muted">
                Par agent
              </p>
              {agents.map((row, index) => {
                const pct =
                  maxAgentCost > 0
                    ? Math.round((row.cost_usd / maxAgentCost) * 100)
                    : 0;
                const barColor =
                  agentBarColors[index % agentBarColors.length];
                return (
                  <div key={row.agent} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-cf-text">
                        {row.agent
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (c) => c.toUpperCase())}
                      </p>
                      <p className="shrink-0 font-mono text-[11px] font-semibold tabular-nums text-cf-muted">
                        {formatEurFromUsd(row.cost_usd)}
                      </p>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full border border-[rgba(0,212,255,0.1)] bg-[#0d0d14]">
                      <div
                        className={`h-full ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}

          {providers.length > 0 ? (
            <div className="mt-6 space-y-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cf-muted">
                Par fournisseur
              </p>
              {providers.map((row, index) => {
                const pct =
                  maxProviderCost > 0
                    ? Math.round((row.cost_usd / maxProviderCost) * 100)
                    : 0;
                return (
                  <div key={row.provider} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-cf-text">
                        {formatProviderLabel(row.provider)}
                      </p>
                      <p className="shrink-0 font-mono text-[11px] font-semibold tabular-nums text-cf-muted">
                        {formatEurFromUsd(row.cost_usd)}
                      </p>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full border border-[rgba(0,212,255,0.1)] bg-[#0d0d14]">
                      <div
                        className={`h-full ${providerBarColor(index)}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
