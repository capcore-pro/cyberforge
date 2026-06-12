import { useMemo } from "react";
import {
  mergeGenerationEntries,
  USD_TO_EUR,
  type AuditGenerationEvent,
  type OrchestrationSession,
} from "@/lib/dashboard-api";
import { GENERATOR_KINDS } from "@/lib/generator-kinds";
import type { AppPage } from "@/lib/navigation";

interface RecentGenerationsWidgetProps {
  sessions: OrchestrationSession[];
  generations: AuditGenerationEvent[];
  loading?: boolean;
  onNavigate: (page: AppPage) => void;
}

const eurPreciseFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const deltaMs = Date.now() - date.getTime();
  if (!Number.isFinite(deltaMs)) return iso;
  const mins = Math.max(0, Math.round(deltaMs / 60_000));
  if (mins < 2) return "à l'instant";
  if (mins < 60) return `il y a ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.round(hours / 24);
  return `il y a ${days} j`;
}

function projectTypeLabel(type: string): string {
  const fromKind = GENERATOR_KINDS.find((k) => k.projectType === type);
  return fromKind?.title ?? type.replace(/_/g, " ");
}

function projectTypeIcon(type: string): string {
  const normalized = type.toLowerCase();
  if (normalized.includes("vitrine") || normalized === "site_vitrine") {
    return "ti ti-home";
  }
  if (normalized.includes("ecommerce") || normalized.includes("e-commerce")) {
    return "ti ti-shopping-cart";
  }
  if (normalized.includes("reservation")) {
    return "ti ti-calendar";
  }
  if (normalized.includes("crm")) {
    return "ti ti-users";
  }
  if (normalized.includes("app_web") || normalized.includes("application")) {
    return "ti ti-apps";
  }
  if (normalized.includes("extension")) {
    return "ti ti-puzzle";
  }
  return "ti ti-file-code";
}

function statusClasses(status: string): {
  dot: string;
  label: string;
} {
  const s = status.toLowerCase();
  if (s === "completed" || s === "success") {
    return {
      dot: "bg-teal-400",
      label: "text-teal-200",
    };
  }
  if (s === "failed" || s === "error") {
    return {
      dot: "bg-red-400",
      label: "text-red-200",
    };
  }
  return {
    dot: "bg-amber-400 animate-pulse",
    label: "text-amber-200",
  };
}

function formatCostEur(usd: number): string {
  return eurPreciseFmt.format(usd * USD_TO_EUR);
}

export function RecentGenerationsWidget({
  sessions,
  generations,
  loading,
  onNavigate,
}: RecentGenerationsWidgetProps) {
  const entries = useMemo(
    () => mergeGenerationEntries(sessions, generations),
    [sessions, generations],
  );

  return (
    <div className="rounded-card border border-white/10 bg-white/5 p-5 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur-xl">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className="inline-flex h-7 w-7 items-center justify-center rounded-control border border-white/10 bg-white/5 text-cf-gold"
            aria-hidden
          >
            <i className="ti ti-history text-sm" />
          </span>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
            Dernières générations
          </h2>
        </div>
        <button
          type="button"
          onClick={() => onNavigate("projects")}
          className="text-[11px] font-semibold text-cf-gold hover:text-cf-gold-hover"
        >
          Voir tout →
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
      ) : entries.length === 0 ? (
        <div className="rounded-control border border-white/10 bg-white/5 p-4">
          <p className="text-sm text-cf-body">
            Aucune génération — lancez votre première création
          </p>
          <button
            type="button"
            onClick={() => onNavigate("generator")}
            className="mt-3 text-[11px] font-semibold text-cf-gold hover:text-cf-gold-hover"
          >
            Créer →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => {
            const statusStyle = statusClasses(entry.status);
            const typeLabel = entry.projectType
              ? projectTypeLabel(entry.projectType)
              : "Génération";
            return (
              <button
                key={entry.generationId}
                type="button"
                onClick={() => onNavigate("projects")}
                className="group flex w-full flex-col gap-2 rounded-control border border-white/10 bg-white/5 p-3 text-left transition hover:border-cf-gold/35 hover:bg-white/7 hover:shadow-gold focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-gold/50"
              >
                <div className="flex items-start gap-3">
                  <span
                    className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-white/10 bg-white/5 text-cf-gold"
                    aria-hidden
                  >
                    <i className={projectTypeIcon(entry.projectType)} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-cf-text">
                      {entry.clientName}
                    </p>
                    <p className="mt-0.5 text-[11px] text-cf-muted">
                      {typeLabel} · {formatRelativeTime(entry.createdAt)}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 pl-11">
                  <span
                    className={`inline-flex items-center gap-1.5 text-[11px] font-semibold ${statusStyle.label}`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${statusStyle.dot}`}
                      aria-hidden
                    />
                    {entry.status}
                  </span>
                  <div className="flex items-center gap-3 text-[11px] text-cf-muted">
                    {entry.qualityScore != null ? (
                      <span>Score: {Math.round(entry.qualityScore)}/100</span>
                    ) : null}
                    {entry.costUsd != null && entry.costUsd > 0 ? (
                      <span className="tabular-nums">
                        {formatCostEur(entry.costUsd)}
                      </span>
                    ) : null}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
