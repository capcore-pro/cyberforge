import { useCallback, useEffect, useMemo, useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { ProjectRecord, ProjectType } from "@shared/types";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { apiRequest } from "@/lib/api-client";
import {
  fetchCockpitAlerts,
  fetchCockpitDashboard,
  type CockpitAlert,
} from "@/lib/cockpit-api";
import { fetchLegalClients } from "@/lib/legal-api";
import {
  GENERATOR_KINDS,
  resolveGenerationMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import { getUserFirstName } from "@/lib/user-preferences";
import type { AppPage } from "@/lib/navigation";

interface DashboardPageProps {
  onNavigate: (page: AppPage) => void;
}

type DashboardProjectKind = GeneratorKindId;

/** Types proposés sur le tableau de bord (sans app desktop). */
const DASHBOARD_KINDS = GENERATOR_KINDS.filter((k) => k.id !== "desktop");

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

function formatEur(value: number): string {
  return eurFmt.format(value);
}

function projectTypeLabel(type: string): string {
  return PROJECT_TYPE_OPTIONS.find((o) => o.id === type)?.label ?? type;
}

function formatRelativeDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function alertTone(level: CockpitAlert["level"]): string {
  if (level === "urgent") return "border-red-500/40 bg-red-950/30 text-red-200";
  if (level === "critical") return "border-cf-alert/40 bg-cf-alert/10 text-cf-alert";
  return "border-cf-info/30 bg-cf-info/10 text-cf-info";
}

function MetricCard({
  label,
  value,
  sub,
  loading,
}: {
  label: string;
  value: string;
  sub?: string;
  loading?: boolean;
}) {
  return (
    <div className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card">
      <p className="cf-section-label">{label}</p>
      <p
        className={`mt-2 text-2xl font-medium tabular-nums text-cf-text ${
          loading ? "animate-pulse text-cf-muted" : ""
        }`}
      >
        {loading ? "—" : value}
      </p>
      {sub ? <p className="mt-1 text-[11px] text-cf-muted">{sub}</p> : null}
    </div>
  );
}

/**
 * Tableau de bord principal — métriques, générateur rapide, projets et alertes.
 */
export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { status: backendStatus } = useBackendHealth();
  const { activeCount, totalAgents } = useAgentsStatus();
  const { patch } = useGeneratorSession();

  const firstName = getUserFirstName();
  const [selectedKind, setSelectedKind] = useState<DashboardProjectKind>("vitrine");
  const [prompt, setPrompt] = useState("");

  const [loading, setLoading] = useState(true);
  const [revenueMonth, setRevenueMonth] = useState<number | null>(null);
  const [apiCostMonth, setApiCostMonth] = useState<number | null>(null);
  const [clientCount, setClientCount] = useState<number | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [alerts, setAlerts] = useState<CockpitAlert[]>([]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    const [stripeRes, cockpitRes, clientsRes, projectsRes, alertsRes] =
      await Promise.all([
        fetchStripeDashboard(),
        fetchCockpitDashboard(),
        fetchLegalClients(),
        apiRequest<ProjectRecord[]>({ method: "GET", path: `${API_PREFIX}/projects` }),
        fetchCockpitAlerts(20),
      ]);

    if (stripeRes.ok && stripeRes.data) {
      setRevenueMonth(stripeRes.data.revenue_this_month_eur ?? 0);
    } else {
      setRevenueMonth(0);
    }

    if (cockpitRes.ok && cockpitRes.data) {
      const dash = cockpitRes.data;
      setApiCostMonth(
        dash.spent_month_eur ??
          dash.expenses?.month_eur ??
          dash.month_total_eur ??
          0,
      );
    } else {
      setApiCostMonth(0);
    }

    if (clientsRes.ok && Array.isArray(clientsRes.data)) {
      setClientCount(clientsRes.data.length);
    } else {
      setClientCount(0);
    }

    if (projectsRes.ok && Array.isArray(projectsRes.data)) {
      setProjects(projectsRes.data);
    } else {
      setProjects([]);
    }

    if (alertsRes.ok && Array.isArray(alertsRes.data)) {
      setAlerts(alertsRes.data);
    } else {
      setAlerts([]);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const recentProjects = useMemo(() => {
    return [...projects]
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      )
      .slice(0, 5);
  }, [projects]);

  const activeProjectsCount = projects.length;
  const backendOnline = backendStatus === "online";

  const handleGenerate = () => {
    const kind =
      GENERATOR_KINDS.find((k) => k.id === selectedKind) ?? GENERATOR_KINDS[0];
    const trimmed = prompt.trim() || kind.defaultDescription || "";
    patch({
      projectType: kind.projectType,
      generationMode: resolveGenerationMode(kind.id, "real"),
      prompt: trimmed,
      phase: "idle",
      error: null,
      actionError: null,
      result: null,
    });
    onNavigate("generator");
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      {/* En-tête */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="cf-page-title">Bonjour {firstName}</h1>
          <p className="mt-1 text-sm text-cf-muted">
            Vue d&apos;ensemble de votre activité CapCore
          </p>
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${
            backendOnline
              ? "border-cf-success/40 bg-cf-success/10 text-cf-success"
              : "border-red-500/40 bg-red-950/40 text-red-300"
          }`}
        >
          {backendOnline
            ? `${activeCount}/${totalAgents} agents actifs`
            : "Hors ligne"}
        </span>
      </header>

      {/* Métriques */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="CA ce mois"
          value={formatEur(revenueMonth ?? 0)}
          loading={loading && revenueMonth === null}
        />
        <MetricCard
          label="Projets actifs"
          value={String(activeProjectsCount)}
          sub="Depuis Supabase"
          loading={loading && projects.length === 0 && activeProjectsCount === 0}
        />
        <MetricCard
          label="Clients"
          value={String(clientCount ?? 0)}
          loading={loading && clientCount === null}
        />
        <MetricCard
          label="Coût API ce mois"
          value={formatEur(apiCostMonth ?? 0)}
          sub="Cockpit FinOps"
          loading={loading && apiCostMonth === null}
        />
      </section>

      {/* Nouveau projet */}
      <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
        <h2 className="cf-section-label mb-4">Nouveau projet</h2>
        <div className="mb-4 flex flex-wrap gap-2">
          {DASHBOARD_KINDS.map((kind) => (
            <button
              key={kind.id}
              type="button"
              onClick={() => setSelectedKind(kind.id)}
              className={`flex items-center gap-2 rounded-control border px-3 py-2 text-sm transition ${
                selectedKind === kind.id
                  ? "border-cf-gold bg-cf-active text-cf-gold"
                  : "border-cf-border-input bg-cf-secondary text-cf-muted hover:border-cf-gold/40 hover:text-cf-text"
              }`}
            >
              <span className="text-cf-gold" aria-hidden>
                {kind.icon}
              </span>
              {kind.title}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <input
            type="text"
            className="cyber-input min-h-[44px] flex-1"
            placeholder="Décrivez votre projet en quelques mots..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleGenerate();
            }}
          />
          <button
            type="button"
            className="cyber-btn shrink-0 px-8 py-2.5 font-medium"
            onClick={handleGenerate}
          >
            Générer
          </button>
        </div>
      </section>

      {/* Deux colonnes */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="cf-section-label">Projets récents</h2>
            <button
              type="button"
              className="text-[11px] text-cf-gold hover:text-cf-gold-hover"
              onClick={() => onNavigate("projects")}
            >
              Tout voir
            </button>
          </div>
          {loading ? (
            <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
          ) : recentProjects.length === 0 ? (
            <p className="text-sm text-cf-muted">Aucun projet pour le moment.</p>
          ) : (
            <ul className="divide-y divide-cf-border">
              {recentProjects.map((project) => (
                <li
                  key={project.id}
                  className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-cf-text">
                      {project.title || "Sans titre"}
                    </p>
                    <p className="mt-0.5 text-[11px] text-cf-muted">
                      {projectTypeLabel(project.project_type)} ·{" "}
                      {formatRelativeDate(project.updated_at)}
                    </p>
                  </div>
                  <span className="shrink-0 rounded border border-cf-border-input bg-cf-secondary px-2 py-0.5 text-[10px] uppercase tracking-wide text-cf-muted">
                    {project.generation_count > 0
                      ? `${project.generation_count} gen.`
                      : "Nouveau"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="cf-section-label">Alertes</h2>
            <button
              type="button"
              className="text-[11px] text-cf-gold hover:text-cf-gold-hover"
              onClick={() => onNavigate("cockpit")}
            >
              Cockpit
            </button>
          </div>
          {loading ? (
            <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-cf-muted">Aucune alerte non lue.</p>
          ) : (
            <ul className="space-y-2">
              {alerts.map((alert) => (
                <li
                  key={alert.id}
                  className={`rounded-control border px-3 py-2.5 text-xs ${alertTone(alert.level)}`}
                >
                  <p className="font-medium">{alert.message}</p>
                  <p className="mt-1 text-[10px] opacity-80">
                    {formatRelativeDate(alert.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
