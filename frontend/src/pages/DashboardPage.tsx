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
import type { AgentStatusItem, ProjectRecord } from "@shared/types";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { apiRequest } from "@/lib/api-client";
import { fetchLegalClients, type LegalClient } from "@/lib/legal-api";
import {
  GENERATOR_KINDS,
  resolveGenerationMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import { getUserFirstName } from "@/lib/user-preferences";
import type { AppPage } from "@/lib/navigation";
import {
  fetchStripeDashboard,
  STRIPE_CAPCORE_PROJECT_ID,
} from "@/lib/stripe-api";
import {
  fetchLLMStats,
  fetchRecentGenerations,
  fetchRecentSessions,
  fetchSupervisorStats,
  USD_TO_EUR,
  type AuditGenerationEvent,
  type LLMStats,
  type OrchestrationSession,
  type SupervisorStats,
} from "@/lib/dashboard-api";
import { fetchAgentRegistry, type AgentRegistryEntry } from "@/lib/agents-api";
import { fetchPoseGallery } from "@/lib/visual-api";
import { LLMCostWidget } from "@/components/dashboard/LLMCostWidget";
import { PipelineHealthWidget } from "@/components/dashboard/PipelineHealthWidget";
import { RecentGenerationsWidget } from "@/components/dashboard/RecentGenerationsWidget";

interface DashboardPageProps {
  onNavigate: (page: AppPage) => void;
}

type DashboardProjectKind = GeneratorKindId;
type AccentColor = "cyan" | "amber" | "purple" | "green";

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12]";
const V2_PANEL_TITLE = "font-mono text-xs tracking-wide text-cf-cyan";

const ACCENT_TOP: Record<AccentColor, string> = {
  cyan: "#00d4ff",
  amber: "#f59e0b",
  purple: "#7c3aed",
  green: "#00ff88",
};

const API_BUDGET_EUR = 20;

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const eurPreciseFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatEur(value: number): string {
  return eurFmt.format(value);
}

function formatEurPrecise(value: number): string {
  return eurPreciseFmt.format(value);
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

function StatCardV2({
  label,
  value,
  sub,
  accentColor,
  loading,
  delayMs = 0,
}: {
  label: string;
  value: string | number;
  sub: string;
  accentColor: AccentColor;
  loading?: boolean;
  delayMs?: number;
}) {
  return (
    <div
      className={`${V2_CARD} p-4`}
      style={{
        borderTop: `2px solid ${ACCENT_TOP[accentColor]}`,
        animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
        animationDelay: `${delayMs}ms`,
      }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cf-muted">
        {label}
      </p>
      <p
        className={[
          "mt-2 font-mono text-3xl font-semibold tabular-nums text-cf-text",
          loading ? "animate-pulse text-cf-muted" : "",
        ].join(" ")}
      >
        {loading ? "—" : value}
      </p>
      <p className="mt-1.5 text-[11px] text-cf-muted">{sub}</p>
    </div>
  );
}

function AgentsPanelV2({
  agents,
  modelById,
  loading,
}: {
  agents: AgentStatusItem[];
  modelById: Map<string, string>;
  loading?: boolean;
}) {
  const pipelineAgents = useMemo(
    () => agents.filter((a) => a.in_pipeline).slice(0, 8),
    [agents],
  );

  return (
    <div className={`${V2_CARD} p-5`}>
      <h2 className={`mb-4 ${V2_PANEL_TITLE}`}>// agents IA</h2>
      {loading ? (
        <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
      ) : pipelineAgents.length === 0 ? (
        <p className="text-sm text-cf-muted">Aucun agent pipeline disponible.</p>
      ) : (
        <ul className="space-y-2.5">
          {pipelineAgents.map((agent) => {
            const isActive = agent.status === "active";
            const model =
              modelById.get(agent.id) ??
              modelById.get(agent.name.toLowerCase()) ??
              "—";
            return (
              <li
                key={agent.id}
                className="flex items-center gap-3 rounded-control border border-[rgba(0,212,255,0.08)] bg-[#0d0d14] px-3 py-2"
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{
                    backgroundColor: isActive ? "#00ff88" : "#f59e0b",
                    boxShadow: isActive
                      ? "0 0 6px rgba(0,255,136,0.5)"
                      : "0 0 6px rgba(245,158,11,0.4)",
                  }}
                  aria-hidden
                />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-cf-text">
                  {agent.name}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-cf-muted">
                  {model}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function V2SectionCard({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div className={`${V2_CARD} p-5 ${className}`} style={style}>
      {children}
    </div>
  );
}

/**
 * Tableau de bord principal — métriques V2, agents, activité et générateur rapide.
 */
export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { status: agentsStatus, loading: agentsLoading } = useAgentsStatus();
  const { patch } = useGeneratorSession();

  const firstName = getUserFirstName();

  const [loading, setLoading] = useState(true);
  const [mrrEur, setMrrEur] = useState(0);
  const [clients, setClients] = useState<LegalClient[]>([]);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [llmStats, setLlmStats] = useState<LLMStats | null>(null);
  const [supervisorStats, setSupervisorStats] = useState<SupervisorStats | null>(
    null,
  );
  const [recentSessions, setRecentSessions] = useState<OrchestrationSession[]>(
    [],
  );
  const [recentGenerations, setRecentGenerations] = useState<
    AuditGenerationEvent[]
  >([]);
  const [agentRegistry, setAgentRegistry] = useState<AgentRegistryEntry[]>([]);
  const [posesCount, setPosesCount] = useState(0);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    const [
      clientsRes,
      projectsRes,
      stripeRes,
      llmRes,
      supervisorRes,
      sessionsRes,
      generationsRes,
      registryRes,
    ] = await Promise.all([
      fetchLegalClients(),
      apiRequest<ProjectRecord[]>({ method: "GET", path: `${API_PREFIX}/projects` }),
      fetchStripeDashboard(STRIPE_CAPCORE_PROJECT_ID),
      fetchLLMStats(),
      fetchSupervisorStats(),
      fetchRecentSessions(5),
      fetchRecentGenerations(5),
      fetchAgentRegistry().catch(() => [] as AgentRegistryEntry[]),
      fetchPoseGallery()
        .then((poses) => setPosesCount(poses.length))
        .catch(() => setPosesCount(0)),
    ]);

    if (clientsRes.ok && Array.isArray(clientsRes.data)) {
      setClients(clientsRes.data);
    } else {
      setClients([]);
    }

    if (projectsRes.ok && Array.isArray(projectsRes.data)) {
      setProjects(projectsRes.data);
    } else {
      setProjects([]);
    }

    if (stripeRes.ok && stripeRes.data) {
      setMrrEur(stripeRes.data.active_subscriptions_mrr_eur ?? 0);
    } else {
      setMrrEur(0);
    }

    setAgentRegistry(registryRes);
    setLlmStats(llmRes);
    setSupervisorStats(supervisorRes);
    setRecentSessions(sessionsRes);
    setRecentGenerations(generationsRes);

    setLoading(false);
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const projectsCount = projects.length;
  const projectsThisMonth = useMemo(
    () => projects.filter((p) => isThisMonth(p.created_at)).length,
    [projects],
  );
  const clientCount = clients.length;

  const llmCostUsd = llmStats?.monthly?.total_cost_usd ?? 0;
  const llmCostEur = llmCostUsd * USD_TO_EUR;
  const fluxCostEur = posesCount * 0.04;

  const modelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const entry of agentRegistry) {
      const label = entry.model ?? entry.provider ?? "—";
      map.set(entry.agent_id, label);
      if (entry.slug) map.set(entry.slug, label);
    }
    return map;
  }, [agentRegistry]);

  const kpiProjects = useCountUp(projectsCount, { enabled: !loading });
  const kpiClients = useCountUp(clientCount, { enabled: !loading });
  const kpiPoses = useCountUp(posesCount, { enabled: !loading });
  const kpiLlmCost = useCountUp(llmCostEur, { enabled: !loading });

  const activeAgentsCount = agentsStatus?.active_count ?? 0;

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

  const today = useMemo(() => new Date(), []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 font-sans">
      <style>{`
        @keyframes cfFadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
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
            <span className="text-cf-cyan">👋</span>
          </h1>
          <p className="mt-2 text-sm text-cf-body">Vue d&apos;ensemble CapCore</p>
        </div>

        <span className="inline-flex items-center gap-2 rounded-full border border-cf-cyan/30 bg-cf-cyan/10 px-3 py-1.5 text-xs font-semibold text-cf-cyan shadow-glow-cyan">
          <span
            className="h-2 w-2 rounded-full bg-cf-cyan shadow-[0_0_8px_rgba(0,212,255,0.6)]"
            aria-hidden
          />
          {agentsLoading ? "…" : activeAgentsCount} agents actifs
        </span>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCardV2
          label="Projets générés"
          value={Math.round(kpiProjects)}
          sub={`+${projectsThisMonth} ce mois`}
          accentColor="cyan"
          loading={loading && projects.length === 0}
          delayMs={60}
        />
        <StatCardV2
          label="Coût API mois"
          value={formatEurPrecise(kpiLlmCost)}
          sub={`budget : ${formatEur(API_BUDGET_EUR)}`}
          accentColor="amber"
          loading={loading}
          delayMs={120}
        />
        <StatCardV2
          label="Clients actifs"
          value={Math.round(kpiClients)}
          sub={`MRR : ${formatEurPrecise(mrrEur)}`}
          accentColor="purple"
          loading={loading}
          delayMs={180}
        />
        <StatCardV2
          label="Visuels FLUX"
          value={Math.round(kpiPoses)}
          sub={`~${fluxCostEur.toFixed(2)} € total`}
          accentColor="green"
          loading={loading}
          delayMs={240}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <AgentsPanelV2
          agents={agentsStatus?.agents ?? []}
          modelById={modelById}
          loading={agentsLoading && !agentsStatus}
        />
        <RecentGenerationsWidget
          sessions={recentSessions}
          generations={recentGenerations}
          loading={loading}
          onNavigate={onNavigate}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <LLMCostWidget data={llmStats} loading={loading} />
        <PipelineHealthWidget data={supervisorStats} loading={loading} />
      </div>

      <V2SectionCard
        style={{
          animation: `cfFadeUp 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both`,
          animationDelay: "340ms",
        }}
      >
        <h2 className="mb-4 text-sm font-semibold tracking-tight text-cf-text">
          ✦ Créer un projet
        </h2>
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
              className="group flex flex-col gap-1.5 rounded-control border border-[rgba(0,212,255,0.15)] bg-[#0d0d14] p-3 text-left transition hover:border-cf-cyan/40 hover:bg-cf-cyan/5 hover:shadow-glow-cyan focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-cyan/50"
            >
              <div className="flex items-center justify-between">
                <span className="text-cf-cyan" aria-hidden>
                  {k.icon}
                </span>
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cf-muted transition group-hover:text-cf-cyan"
                  aria-hidden
                >
                  →
                </span>
              </div>
              <p className="text-sm font-medium text-cf-text">{k.label}</p>
              <p className="text-[11px] text-cf-muted">Ouvrir le générateur</p>
            </button>
          ))}
        </div>
      </V2SectionCard>
    </div>
  );
}
