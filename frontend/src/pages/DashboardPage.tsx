import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { API_PREFIX } from "@shared/constants";
import type { ProjectRecord } from "@shared/types";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { apiRequest } from "@/lib/api-client";
import { fetchLegalClients } from "@/lib/legal-api";
import {
  GENERATOR_KINDS,
  resolveGenerationMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import { getUserFirstName } from "@/lib/user-preferences";
import type { AppPage } from "@/lib/navigation";
import {
  fetchSystemNotifications,
  type SystemNotification,
} from "@/lib/system-notifications-api";

interface DashboardPageProps {
  onNavigate: (page: AppPage) => void;
}

type DashboardProjectKind = GeneratorKindId;

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
  const fromKind = GENERATOR_KINDS.find((k) => k.projectType === type);
  return fromKind?.title ?? type;
}

function formatDayDate(now: Date): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(now);
  } catch {
    return now.toISOString();
  }
}

function formatCompactDate(iso: string): string {
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

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const deltaMs = Date.now() - date.getTime();
  if (!Number.isFinite(deltaMs)) return iso;
  const mins = Math.max(0, Math.round(deltaMs / 60_000));
  if (mins < 2) return "à l’instant";
  if (mins < 60) return `il y a ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.round(hours / 24);
  return `il y a ${days} j`;
}

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

function startOfThisMonth(): Date {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1, 0, 0, 0, 0);
}

function isThisMonth(iso: string): boolean {
  const d = new Date(iso);
  const start = startOfThisMonth().getTime();
  return Number.isFinite(d.getTime()) && d.getTime() >= start;
}

function safeNumber(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function useCountUp(target: number, opts?: { durationMs?: number; enabled?: boolean }) {
  const durationMs = opts?.durationMs ?? 850;
  const enabled = opts?.enabled ?? true;
  const [value, setValue] = useState(0);
  const raf = useRef<number | null>(null);
  const lastTarget = useRef<number>(0);

  useEffect(() => {
    if (!enabled) {
      setValue(target);
      return;
    }
    if (lastTarget.current === target) return;
    lastTarget.current = target;
    if (raf.current) cancelAnimationFrame(raf.current);

    const start = performance.now();
    const from = 0;
    const to = target;

    const tick = (t: number) => {
      const p = clamp((t - start) / durationMs, 0, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const next = from + (to - from) * eased;
      setValue(next);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };

    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [durationMs, enabled, target]);

  return value;
}

function GlassCard({
  children,
  className = "",
  style,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: () => void;
}) {
  const clickable = Boolean(onClick);
  return (
    <div
      onClick={onClick}
      style={style}
      className={[
        "rounded-card border border-white/10 bg-white/5 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur-xl",
        clickable
          ? "cursor-pointer transition hover:border-cf-gold/30 hover:bg-white/7 hover:shadow-gold"
          : "",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}

function SectionTitle({
  icon,
  title,
  action,
}: {
  icon?: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        {icon ? (
          <span
            className="inline-flex h-7 w-7 items-center justify-center rounded-control border border-white/10 bg-white/5 text-sm text-cf-gold"
            aria-hidden
          >
            {icon}
          </span>
        ) : null}
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          {title}
        </h2>
      </div>
      {action}
    </div>
  );
}

function TrendChip({
  valuePct,
}: {
  valuePct: number;
}) {
  const up = valuePct >= 0;
  const pct = Math.abs(valuePct);
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold tabular-nums",
        up
          ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
          : "border-orange-400/20 bg-orange-500/10 text-orange-200",
      ].join(" ")}
      aria-label={`Tendance ${up ? "en hausse" : "en baisse"} de ${pct}%`}
    >
      <span aria-hidden>{up ? "↑" : "↓"}</span>
      {pct}%
    </span>
  );
}

function KpiCard({
  icon,
  iconClassName,
  label,
  value,
  valueSuffix,
  trendPct,
  loading,
  delayMs = 0,
}: {
  icon: string;
  iconClassName: string;
  label: string;
  value: string;
  valueSuffix?: string;
  trendPct: number;
  loading?: boolean;
  delayMs?: number;
}) {
  return (
    <GlassCard
      className="p-4"
      style={{
        animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
        animationDelay: `${delayMs}ms`,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={[
              "flex h-10 w-10 items-center justify-center rounded-control border border-white/10 bg-white/5 text-lg",
              iconClassName,
            ].join(" ")}
            aria-hidden
          >
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cf-muted">
              {label}
            </p>
            <p
              className={[
                "mt-1 truncate text-3xl font-semibold tabular-nums text-cf-text",
                loading ? "animate-pulse text-cf-muted" : "",
              ].join(" ")}
            >
              {loading ? "—" : value}
              {valueSuffix ? (
                <span className="ml-1 text-sm font-medium text-cf-muted">
                  {valueSuffix}
                </span>
              ) : null}
            </p>
          </div>
        </div>
        <TrendChip valuePct={trendPct} />
      </div>
    </GlassCard>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  const p = clamp(pct, 0, 100);
  const color =
    p >= 55 ? "bg-emerald-400" : p >= 30 ? "bg-orange-400" : "bg-red-400";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full border border-white/10 bg-white/5">
      <div className={`h-full ${color}`} style={{ width: `${p}%` }} />
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

  const [loading, setLoading] = useState(true);
  const [revenueMonth, setRevenueMonth] = useState<number | null>(null);
  const [apiCostMonth, setApiCostMonth] = useState<number | null>(null);
  const [clientCount, setClientCount] = useState<number | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    const [clientsRes, projectsRes, notifRes] = await Promise.all([
      fetchLegalClients(),
      apiRequest<ProjectRecord[]>({ method: "GET", path: `${API_PREFIX}/projects` }),
      fetchSystemNotifications(false),
    ]);

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

    if (notifRes.ok && notifRes.data && Array.isArray(notifRes.data.items)) {
      setNotifications(notifRes.data.items);
    } else {
      setNotifications([]);
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
      .slice(0, 3);
  }, [projects]);

  const activeProjectsCount = projects.length;
  const backendOnline = backendStatus === "online";

  const projectsThisMonth = useMemo(() => {
    return projects.filter((p) => isThisMonth(p.created_at));
  }, [projects]);

  const estApiCostMonth = useMemo(() => {
    return projects
      .filter((p) => isThisMonth(p.updated_at))
      .reduce((sum, p) => sum + safeNumber((p as any).latest_estimated_cost_usd), 0);
  }, [projects]);

  const estRevenueMonth = useMemo(() => {
    const AVG_PROJECT_REVENUE_EUR = 2500;
    return projectsThisMonth.length * AVG_PROJECT_REVENUE_EUR;
  }, [projectsThisMonth.length]);

  useEffect(() => {
    setRevenueMonth(estRevenueMonth);
    setApiCostMonth(estApiCostMonth);
  }, [estApiCostMonth, estRevenueMonth]);

  const kpiRevenue = useCountUp(revenueMonth ?? 0, { enabled: !loading });
  const kpiApiCost = useCountUp(apiCostMonth ?? 0, { enabled: !loading });
  const kpiClients = useCountUp(clientCount ?? 0, { enabled: !loading });
  const kpiProjects = useCountUp(activeProjectsCount, { enabled: !loading });

  const openGeneratorPreset = useCallback(
    (kindId: DashboardProjectKind) => {
      const kind =
        GENERATOR_KINDS.find((k) => k.id === kindId) ?? GENERATOR_KINDS[0];
      patch({
        projectType: kind.projectType,
        generationMode: resolveGenerationMode(kind.id, "real"),
        prompt: kind.defaultDescription || "",
        phase: "idle",
        error: null,
        actionError: null,
        result: null,
      });
      onNavigate("generator");
    },
    [onNavigate, patch],
  );

  const handleGenerateFromKind = (kindId: DashboardProjectKind) => {
    const kind =
      GENERATOR_KINDS.find((k) => k.id === kindId) ?? GENERATOR_KINDS[0];
    patch({
      projectType: kind.projectType,
      generationMode: resolveGenerationMode(kind.id, "real"),
      prompt: kind.defaultDescription || "",
      phase: "idle",
      error: null,
      actionError: null,
      result: null,
    });
    onNavigate("generator");
  };

  const today = useMemo(() => new Date(), []);
  const activity = useMemo(() => notifications.slice(0, 5), [notifications]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <style>{`
        @keyframes cfFadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes cfPulseDot {
          0% { transform: scale(1); opacity: 1; }
          60% { transform: scale(1.6); opacity: 0; }
          100% { transform: scale(1.6); opacity: 0; }
        }
      `}</style>

      <header
        style={{ animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both` }}
        className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
            {formatDayDate(today)}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-cf-text md:text-4xl">
            Bonjour {firstName}{" "}
            <span className="text-cf-gold">👋</span>
          </h1>
          <p className="mt-2 text-sm text-cf-body">Vue d&apos;ensemble CapCore</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span
            className={[
              "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold",
              backendOnline
                ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                : "border-red-400/30 bg-red-500/10 text-red-200",
            ].join(" ")}
          >
            <span className="relative inline-flex h-2.5 w-2.5 items-center justify-center">
              <span className="h-2.5 w-2.5 rounded-full bg-current" />
              {backendOnline ? (
                <span
                  className="absolute inset-0 rounded-full bg-current opacity-60"
                  style={{ animation: "cfPulseDot 1.3s ease-out infinite" }}
                  aria-hidden
                />
              ) : null}
            </span>
            {backendOnline ? `${activeCount}/${totalAgents} agents actifs` : "Backend hors ligne"}
          </span>
        </div>
      </header>

      {/* KPIs */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          icon="€"
          iconClassName="text-cf-gold"
          label="CA ce mois"
          value={formatEur(kpiRevenue)}
          trendPct={12}
          loading={loading && revenueMonth === null}
          delayMs={60}
        />
        <KpiCard
          icon="📁"
          iconClassName="text-sky-200"
          label="Projets actifs"
          value={String(Math.round(kpiProjects))}
          trendPct={-3}
          loading={loading && projects.length === 0}
          delayMs={120}
        />
        <KpiCard
          icon="👥"
          iconClassName="text-violet-200"
          label="Clients"
          value={String(Math.round(kpiClients))}
          trendPct={8}
          loading={loading && clientCount === null}
          delayMs={180}
        />
        <KpiCard
          icon="⚡"
          iconClassName="text-orange-200"
          label="Coût API ce mois"
          value={formatEur(kpiApiCost)}
          trendPct={6}
          loading={loading && apiCostMonth === null}
          delayMs={240}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Crédits API */}
        <GlassCard
          className="p-5"
          style={{
            animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
            animationDelay: "300ms",
          }}
        >
          <SectionTitle
            icon="⛽"
            title="Crédits API"
            action={
              <button
                type="button"
                onClick={() => window.cyberforge?.openExternal?.("https://capcore.pro")}
                className="text-[11px] font-semibold text-cf-gold hover:text-cf-gold-hover"
              >
                Recréditer →{/* lien externe */}
              </button>
            }
          />
          <div className="space-y-4">
            {[
              { label: "Anthropic", left: "62%", pct: 62 },
              { label: "Pexels", left: "41%", pct: 41 },
              { label: "Firecrawl", left: "28%", pct: 28 },
              { label: "Brevo", left: "75%", pct: 75 },
            ].map((row) => (
              <div key={row.label} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-cf-text">{row.label}</p>
                  <p className="text-[11px] font-semibold tabular-nums text-cf-muted">
                    Restant estimé {row.left}
                  </p>
                </div>
                <ProgressBar pct={row.pct} />
              </div>
            ))}
          </div>
          <p className="mt-4 text-[11px] text-cf-muted">
            Valeurs statiques pour l’instant — connexion aux quotas à venir.
          </p>
        </GlassCard>

        {/* Démarrer un projet */}
        <GlassCard
          className="p-5"
          style={{
            animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
            animationDelay: "360ms",
          }}
        >
          <SectionTitle icon="➕" title="Démarrer un projet" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              { id: "vitrine" as DashboardProjectKind, label: "Vitrine", icon: "◈" },
              { id: "reservation" as DashboardProjectKind, label: "Réservation", icon: "⏱" },
              { id: "ecommerce" as DashboardProjectKind, label: "E‑commerce", icon: "▤" },
              { id: "app_web" as DashboardProjectKind, label: "App web", icon: "⚡" },
              { id: "extension" as DashboardProjectKind, label: "Extension", icon: "◇" },
              { id: "desktop" as DashboardProjectKind, label: "App desktop", icon: "▥" },
            ].map((k) => (
              <button
                key={k.id}
                type="button"
                onClick={() => openGeneratorPreset(k.id)}
                className="group flex flex-col gap-1.5 rounded-control border border-white/10 bg-white/5 p-3 text-left transition hover:border-cf-gold/35 hover:bg-white/7 hover:shadow-gold focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-gold/50"
              >
                <div className="flex items-center justify-between">
                  <span className="text-cf-gold" aria-hidden>
                    {k.icon}
                  </span>
                  <span
                    className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cf-muted transition group-hover:text-cf-gold"
                    aria-hidden
                  >
                    →
                  </span>
                </div>
                <p className="text-sm font-medium text-cf-text">{k.label}</p>
                <p className="text-[11px] text-cf-muted">
                  Ouvrir le générateur
                </p>
              </button>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Projets récents */}
        <GlassCard
          className="p-5"
          style={{
            animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
            animationDelay: "420ms",
          }}
        >
          <SectionTitle
            icon="▤"
            title="Projets récents"
            action={
              <button
                type="button"
                className="text-[11px] font-semibold text-cf-gold hover:text-cf-gold-hover"
                onClick={() => onNavigate("projects")}
              >
                Tout voir →
              </button>
            }
          />

          {loading ? (
            <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
          ) : recentProjects.length === 0 ? (
            <div className="rounded-control border border-white/10 bg-white/5 p-4">
              <p className="text-sm text-cf-body">
                Aucun projet — créez votre premier{" "}
                <button
                  type="button"
                  className="font-semibold text-cf-gold hover:text-cf-gold-hover"
                  onClick={() => handleGenerateFromKind("vitrine")}
                >
                  ↗
                </button>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentProjects.map((project) => {
                const isOnline = Boolean((project as any).demo_url?.trim?.());
                const previewHtml = (project as any).preview_html as
                  | string
                  | undefined
                  | null;
                return (
                  <button
                    key={project.id}
                    type="button"
                    onClick={() => onNavigate("projects")}
                    className="group flex w-full items-start gap-3 rounded-control border border-white/10 bg-white/5 p-3 text-left transition hover:border-cf-gold/35 hover:bg-white/7 hover:shadow-gold focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-gold/50"
                  >
                    <div className="h-[72px] w-[128px] shrink-0 overflow-hidden rounded-md border border-white/10 bg-black/40">
                      {previewHtml?.trim() ? (
                        <iframe
                          title={`Miniature ${project.title}`}
                          className="h-full w-full origin-top-left"
                          sandbox="allow-scripts allow-same-origin allow-forms"
                          srcDoc={previewHtml}
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                          Aperçu
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-cf-text">
                            {project.title || "Sans titre"}
                          </p>
                          <p className="mt-0.5 text-[11px] text-cf-muted">
                            {projectTypeLabel(project.project_type)} ·{" "}
                            {formatCompactDate(project.updated_at)}
                          </p>
                        </div>
                        <span
                          className={[
                            "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]",
                            isOnline
                              ? "border-emerald-400/25 bg-emerald-500/10 text-emerald-200"
                              : "border-white/10 bg-white/5 text-cf-muted",
                          ].join(" ")}
                        >
                          {isOnline ? "En ligne" : "Hors ligne"}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-cf-muted">
                          {(project.generation_count ?? 0) > 0
                            ? `${project.generation_count} génération(s)`
                            : "Nouveau"}
                        </span>
                        <span className="text-[11px] font-semibold text-cf-gold group-hover:text-cf-gold-hover">
                          Ouvrir →
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </GlassCard>

        {/* Activité récente */}
        <GlassCard
          className="p-5"
          style={{
            animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
            animationDelay: "480ms",
          }}
        >
          <SectionTitle icon="⏺" title="Activité récente" />
          {loading ? (
            <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
          ) : activity.length === 0 ? (
            <p className="text-sm text-cf-muted">
              Aucune activité récente.
            </p>
          ) : (
            <ol className="relative space-y-4 pl-5">
              <div className="absolute bottom-0 left-[10px] top-0 w-px bg-white/10" />
              {activity.map((n) => (
                <li key={n.id} className="relative">
                  <div className="absolute -left-[2px] top-1.5 h-3 w-3 rounded-full border border-white/20 bg-cf-gold shadow-gold" />
                  <div className="rounded-control border border-white/10 bg-white/5 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-cf-text">
                          {n.title}
                        </p>
                        {n.message ? (
                          <p className="mt-1 line-clamp-2 text-[11px] text-cf-body">
                            {n.message}
                          </p>
                        ) : null}
                      </div>
                      <span className="shrink-0 text-[11px] font-semibold text-cf-muted">
                        {formatRelativeTime(n.created_at)}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
