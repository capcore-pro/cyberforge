import type { LLMStats } from "@/lib/dashboard-api";
import { USD_TO_EUR } from "@/lib/dashboard-api";

interface LLMCostWidgetProps {
  data: LLMStats | null;
  loading?: boolean;
}

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
  if (key.includes("mistral") && key.includes("small")) return "Mistral Small";
  if (key.includes("mistral") && key.includes("large")) return "Mistral Large";
  return provider
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function providerBarColor(provider: string): string {
  const key = provider.toLowerCase();
  if (key === "mistral") return "bg-[#f97316]";
  if (key.includes("anthropic")) return "bg-cf-gold";
  if (key.includes("openai")) return "bg-teal-400";
  return "bg-white/40";
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
    .filter((row) => row.provider.toLowerCase() === "mistral" || row.cost_usd > 0)
    .sort((a, b) => b.cost_usd - a.cost_usd);
  const maxAgentCost = agents.length > 0 ? agents[0].cost_usd : 0;
  const maxProviderCost =
    providers.length > 0 ? providers[0].cost_usd : 0;

  return (
    <div className="rounded-card border border-white/10 bg-white/5 p-5 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur-xl">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className="inline-flex h-7 w-7 items-center justify-center rounded-control border border-white/10 bg-white/5 text-cf-gold"
            aria-hidden
          >
            <i className="ti ti-coin text-sm" />
          </span>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
            Coût LLM ce mois
          </h2>
        </div>
        <span className="rounded-full border border-teal-400/30 bg-teal-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-teal-200">
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
          <p className="text-3xl font-semibold tabular-nums text-cf-text">
            {formatEurFromUsd(totalUsd)}
          </p>
          <p className="mt-1 text-sm text-white/40">
            {totalTokens.toLocaleString("fr-FR")} tokens
          </p>

          {agents.length > 0 ? (
            <div className="mt-5 space-y-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                Par agent
              </p>
              {agents.map((row) => {
                const pct =
                  maxAgentCost > 0
                    ? Math.round((row.cost_usd / maxAgentCost) * 100)
                    : 0;
                const shareOfTotal =
                  totalUsd > 0 ? row.cost_usd / totalUsd : 0;
                const barColor =
                  shareOfTotal > 0.5 ? "bg-cf-gold" : "bg-teal-400";
                return (
                  <div key={row.agent} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-cf-text">
                        {row.agent
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (c) => c.toUpperCase())}
                      </p>
                      <p className="shrink-0 text-[11px] font-semibold tabular-nums text-cf-muted">
                        {formatEurFromUsd(row.cost_usd)}
                      </p>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full border border-white/10 bg-white/5">
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
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                Par fournisseur
              </p>
              {providers.map((row) => {
                const pct =
                  maxProviderCost > 0
                    ? Math.round((row.cost_usd / maxProviderCost) * 100)
                    : 0;
                const isMistral = row.provider.toLowerCase() === "mistral";
                return (
                  <div key={row.provider} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <p
                        className={`truncate text-sm font-medium ${
                          isMistral ? "text-[#f97316]" : "text-cf-text"
                        }`}
                      >
                        {formatProviderLabel(row.provider)}
                        {isMistral ? (
                          <span className="ml-2 text-[10px] text-[#f59e0b]">
                            volume coulisses
                          </span>
                        ) : null}
                      </p>
                      <p className="shrink-0 text-[11px] font-semibold tabular-nums text-cf-muted">
                        {formatEurFromUsd(row.cost_usd)}
                      </p>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full border border-white/10 bg-white/5">
                      <div
                        className={`h-full ${providerBarColor(row.provider)}`}
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
