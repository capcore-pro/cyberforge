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

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12]";

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

function projectTypeIconColor(type: string): string {
  const normalized = type.toLowerCase();
  if (normalized.includes("vitrine") || normalized === "site_vitrine") {
    return "text-cf-cyan border-cf-cyan/30 bg-cf-cyan/10";
  }
  if (normalized.includes("ecommerce") || normalized.includes("e-commerce")) {
    return "text-cf-purple border-cf-purple/30 bg-cf-purple/10";
  }
  if (normalized.includes("reservation")) {
    return "text-[#f59e0b] border-[#f59e0b]/30 bg-[#f59e0b]/10";
  }
  if (normalized.includes("extension")) {
    return "text-cf-green border-cf-green/30 bg-cf-green/10";
  }
  return "text-cf-cyan border-cf-cyan/20 bg-cf-cyan/5";
}

function statusClasses(status: string): {
  dot: string;
  label: string;
} {
  const s = status.toLowerCase();
  if (s === "completed" || s === "success") {
    return {
      dot: "bg-cf-green",
      label: "text-cf-green",
    };
  }
  if (s === "failed" || s === "error") {
    return {
      dot: "bg-cf-red",
      label: "text-cf-red",
    };
  }
  return {
    dot: "bg-[#f59e0b] animate-pulse",
    label: "text-[#f59e0b]",
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
    <div className={`${V2_CARD} p-5`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-mono text-xs tracking-wide text-cf-cyan">
          // activité récente
        </h2>
        <button
          type="button"
          onClick={() => onNavigate("projects")}
          className="font-mono text-[11px] font-semibold text-cf-cyan hover:text-white"
        >
          Voir tout →
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
      ) : entries.length === 0 ? (
        <div className="rounded-control border border-[rgba(0,212,255,0.1)] bg-[#0d0d14] p-4">
          <p className="text-sm text-cf-body">
            Aucune génération — lancez votre première création
          </p>
          <button
            type="button"
            onClick={() => onNavigate("generator")}
            className="mt-3 font-mono text-[11px] font-semibold text-cf-cyan hover:text-white"
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
            const iconColor = projectTypeIconColor(entry.projectType);
            return (
              <button
                key={entry.generationId}
                type="button"
                onClick={() => onNavigate("projects")}
                className="group flex w-full items-center gap-3 rounded-control border border-[rgba(0,212,255,0.1)] bg-[#0d0d14] p-3 text-left transition hover:border-cf-cyan/30 hover:bg-cf-cyan/5 focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-cyan/50"
              >
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-control border ${iconColor}`}
                  aria-hidden
                >
                  <i className={projectTypeIcon(entry.projectType)} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-cf-text">
                    {entry.clientName}
                  </p>
                  <p className="mt-0.5 text-[11px] text-cf-muted">{typeLabel}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span
                    className={`font-mono text-[10px] text-cf-muted`}
                  >
                    {formatRelativeTime(entry.createdAt)}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 font-mono text-[10px] font-semibold ${statusStyle.label}`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${statusStyle.dot}`}
                      aria-hidden
                    />
                    {entry.status}
                  </span>
                  {entry.costUsd != null && entry.costUsd > 0 ? (
                    <span className="font-mono text-[10px] tabular-nums text-cf-muted">
                      {formatCostEur(entry.costUsd)}
                    </span>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
