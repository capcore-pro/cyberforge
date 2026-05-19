import { useEffect, useState } from "react";
import { APP_NAME, DEFAULT_API_BASE_URL } from "@shared/constants";
import { apiRequest, isElectronApiAvailable } from "@/lib/api-client";

type BackendStatus = "loading" | "online" | "offline";

interface HealthInfo {
  app?: string;
  version?: string;
}

interface AgentDef {
  id: string;
  name: string;
  role: string;
  tag: string;
  accent: "cyan" | "violet";
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Tableau de bord", icon: "◈", active: true },
  { id: "agents", label: "Agents", icon: "◇", active: false },
  { id: "tools", label: "Outils", icon: "⬡", active: false },
  { id: "reports", label: "Rapports", icon: "▣", active: false },
  { id: "settings", label: "Paramètres", icon: "⚙", active: false },
] as const;

const AGENTS: AgentDef[] = [
  {
    id: "coremind",
    name: "CoreMindAI",
    role: "Orchestrateur central — planification, priorisation et coordination des agents.",
    tag: "CORE",
    accent: "violet",
  },
  {
    id: "architect",
    name: "ArchitectAI",
    role: "Conception d'architecture sécurisée, modélisation des menaces et choix techniques.",
    tag: "ARCH",
    accent: "cyan",
  },
  {
    id: "builder",
    name: "BuilderAI",
    role: "Génération de code, scaffolding de modules et intégration des bonnes pratiques.",
    tag: "BLD",
    accent: "violet",
  },
  {
    id: "bughunter",
    name: "BugHunterAI",
    role: "Chasse aux vulnérabilités, analyse statique et revue de code orientée sécurité.",
    tag: "HUNT",
    accent: "cyan",
  },
  {
    id: "autofix",
    name: "AutoFixAI",
    role: "Remédiation assistée, correctifs proposés et durcissement automatique.",
    tag: "FIX",
    accent: "violet",
  },
  {
    id: "visionui",
    name: "VisionUI",
    role: "Interfaces visuelles, design system cyber et composants React/Tailwind.",
    tag: "UI",
    accent: "cyan",
  },
  {
    id: "testpilot",
    name: "TestPilotAI",
    role: "Tests automatisés, scénarios E2E et validation de régression.",
    tag: "QA",
    accent: "violet",
  },
  {
    id: "export",
    name: "ExportAI",
    role: "Export de rapports, livrables PDF/JSON et documentation client.",
    tag: "EXP",
    accent: "cyan",
  },
];

function StatusIndicator({ status }: { status: BackendStatus }) {
  const ringClass = {
    loading: "border-cyber-muted text-cyber-muted",
    online: "border-green-400 text-green-400 shadow-[0_0_20px_rgba(74,222,128,0.4)]",
    offline: "border-red-400 text-red-400 shadow-[0_0_20px_rgba(248,113,113,0.35)]",
  }[status];

  const dotClass = {
    loading: "bg-cyber-muted animate-pulse",
    online: "bg-green-400 animate-pulseNeon",
    offline: "bg-red-400",
  }[status];

  return (
    <div className={`cyber-status-ring ${ringClass}`}>
      <span className={`h-3 w-3 rounded-full ${dotClass}`} />
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentDef }) {
  const accentBorder =
    agent.accent === "cyan"
      ? "group-hover:border-cyber-accent"
      : "group-hover:border-cyber-violet";
  const tagClass =
    agent.accent === "cyan"
      ? "border-cyber-accent/40 bg-cyber-accent/10 text-cyber-neon"
      : "border-cyber-violet/40 bg-cyber-violet/10 text-cyber-violet";

  return (
    <article
      className={`cyber-agent-card group ${accentBorder}`}
      aria-label={agent.name}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <span
          className={`rounded border px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest ${tagClass}`}
        >
          {agent.tag}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
          standby
        </span>
      </div>
      <h3 className="mb-1.5 text-sm font-bold text-cyber-text group-hover:text-cyber-neon">
        {agent.name}
      </h3>
      <p className="text-xs leading-relaxed text-cyber-muted">{agent.role}</p>
    </article>
  );
}

/**
 * Page d'accueil — tableau de bord cyber avec agents et statut système.
 */
export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("loading");
  const [health, setHealth] = useState<HealthInfo | null>(null);

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const transportLabel = isElectronApiAvailable()
    ? "IPC → FastAPI"
    : "HTTP direct";
  const electronReady = isElectronApiAvailable();

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      const response = await apiRequest<{
        status?: string;
        app?: string;
        version?: string;
      }>({
        method: "GET",
        path: "/api/health",
      });
      if (!cancelled) {
        setBackendStatus(response.ok ? "online" : "offline");
        if (response.ok && response.data) {
          setHealth({
            app: response.data.app,
            version: response.data.version,
          });
        }
      }
    }

    void checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel = {
    loading: "Initialisation…",
    online: "Système opérationnel",
    offline: "Système hors ligne",
  }[backendStatus];

  const statusSub = {
    loading: "Connexion au backend en cours",
    online: "Tous les services répondent",
    offline: "Impossible de joindre FastAPI",
  }[backendStatus];

  return (
    <div className="flex h-full min-h-0 w-full">
      {/* Navigation latérale */}
      <aside className="cyber-sidebar">
        <div className="border-b border-cyber-border px-4 py-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
            Navigation
          </p>
          <p className="mt-1 text-xs text-cyber-muted">{APP_NAME}</p>
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Navigation principale">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={!item.active}
              className={`cyber-nav-item w-full text-left ${
                item.active ? "cyber-nav-item-active" : ""
              } disabled:cursor-not-allowed disabled:opacity-40`}
            >
              <span className="text-cyber-accent" aria-hidden>
                {item.icon}
              </span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="border-t border-cyber-border p-4">
          <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
            Agents actifs
          </p>
          <p className="mt-1 text-2xl font-bold text-cyber-neon">0 / 8</p>
          <p className="text-[10px] text-cyber-muted">En attente d&apos;activation</p>
        </div>
      </aside>

      {/* Contenu principal */}
      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 bg-cyber-grid bg-cyber-grid opacity-40"
          aria-hidden
        />
        <div className="cyber-scanline" aria-hidden />

        <div className="relative flex-1 overflow-y-auto p-6 md:p-8">
          {/* En-tête hero */}
          <header className="mb-8">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
              // secure_ops_dashboard
            </p>
            <h1
              className="cyber-glitch-title text-3xl md:text-4xl lg:text-5xl"
              data-text={APP_NAME}
            >
              {APP_NAME}
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-cyber-muted">
              Plateforme desktop d&apos;assistance IA pour la cybersécurité.
              Orchestration multi-agents, analyse et remédiation — configurez{" "}
              <code className="rounded border border-cyber-border bg-cyber-surface px-1.5 py-0.5 text-cyber-neon">
                .env
              </code>{" "}
              à la racine avant le déploiement.
            </p>
          </header>

          {/* Statut système */}
          <section
            className="cyber-panel mb-8 overflow-hidden border-cyber-borderGlow bg-gradient-to-br from-cyber-surface via-cyber-surfaceAlt to-cyber-surface p-0"
            aria-labelledby="system-status-heading"
          >
            <div className="border-b border-cyber-border bg-cyber-surfaceAlt/80 px-5 py-3">
              <h2
                id="system-status-heading"
                className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-neon"
              >
                Statut système
              </h2>
            </div>

            <div className="grid gap-6 p-5 sm:grid-cols-[auto_1fr] sm:items-center">
              <StatusIndicator status={backendStatus} />

              <div>
                <p className="text-lg font-semibold text-cyber-text">{statusLabel}</p>
                <p className="text-sm text-cyber-muted">{statusSub}</p>
              </div>

              <div className="col-span-full grid gap-3 sm:col-span-2 sm:grid-cols-2 lg:grid-cols-4">
                <StatusMetric
                  label="Backend FastAPI"
                  value={backendStatus === "online" ? "ONLINE" : backendStatus === "offline" ? "OFFLINE" : "…"}
                  highlight={backendStatus === "online"}
                />
                <StatusMetric
                  label="Transport"
                  value={transportLabel}
                />
                <StatusMetric
                  label="Shell Electron"
                  value={electronReady ? "ACTIF" : "WEB"}
                />
                <StatusMetric
                  label="API"
                  value={health?.version ? `v${health.version}` : "—"}
                  sub={health?.app ?? apiBaseUrl}
                />
              </div>
            </div>

            <div className="border-t border-cyber-border bg-cyber-bg/50 px-5 py-2">
              <p className="truncate font-mono text-[10px] text-cyber-muted">
                <span className="text-cyber-violet">endpoint</span>{" "}
                <span className="text-cyber-neon">{apiBaseUrl}/api/health</span>
              </p>
            </div>
          </section>

          {/* Grille agents */}
          <section aria-labelledby="agents-heading">
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <h2
                  id="agents-heading"
                  className="text-sm font-bold uppercase tracking-[0.2em] text-cyber-violet"
                >
                  Écosystème agents
                </h2>
                <p className="mt-1 text-xs text-cyber-muted">
                  Huit modules spécialisés — prêts pour l&apos;orchestration CoreMindAI
                </p>
              </div>
              <span className="hidden rounded border border-cyber-border px-3 py-1 text-[10px] uppercase tracking-wider text-cyber-muted sm:inline">
                mode: preview
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {AGENTS.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function StatusMetric({
  label,
  value,
  sub,
  highlight = false,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-md border border-cyber-border bg-cyber-bg/60 px-3 py-2.5">
      <p className="text-[10px] uppercase tracking-wider text-cyber-muted">{label}</p>
      <p
        className={`mt-0.5 truncate font-mono text-sm font-bold ${
          highlight ? "text-green-400" : "text-cyber-text"
        }`}
      >
        {value}
      </p>
      {sub ? (
        <p className="mt-0.5 truncate text-[10px] text-cyber-muted">{sub}</p>
      ) : null}
    </div>
  );
}
