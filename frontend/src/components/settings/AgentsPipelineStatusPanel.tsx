import { useAgentsStatus } from "@/context/AgentsStatusContext";

const HIGHLIGHT_IDS = new Set(["research", "openhands"]);

/**
 * Statut visuel des agents du pipeline (GET /api/agents/status).
 */
export function AgentsPipelineStatusPanel() {
  const { status, loading } = useAgentsStatus();
  const agents = status?.agents ?? [];
  const activeCount = agents.filter((a) => a.status === "active").length;
  const totalAgents = agents.length;

  const highlighted = agents.filter((a) => HIGHLIGHT_IDS.has(a.id));
  const others = agents.filter((a) => !HIGHLIGHT_IDS.has(a.id));

  return (
    <div className="mb-6 rounded-card border border-cf-border-input bg-cf-secondary/30 p-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-cf-text">Statut des agents</p>
        {agents.length > 0 ? (
          <p className="text-[11px] text-cf-muted">
            {activeCount} / {totalAgents} actifs
          </p>
        ) : null}
      </div>

      {loading && !status ? (
        <p className="animate-pulse text-xs text-cf-muted">Chargement…</p>
      ) : (
        <div className="space-y-4">
          <ul className="grid gap-2 sm:grid-cols-3">
            {highlighted.map((agent) => (
              <AgentStatusChip key={agent.id} name={agent.name} status={agent.status} />
            ))}
          </ul>
          {others.length > 0 ? (
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {others.map((agent) => (
                <AgentStatusChip key={agent.id} name={agent.name} status={agent.status} compact />
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </div>
  );
}

function AgentStatusChip({
  name,
  status,
  compact = false,
}: {
  name: string;
  status: string;
  compact?: boolean;
}) {
  const active = status === "active";
  return (
    <li
      className={`flex items-center justify-between gap-2 rounded-control border px-3 py-2 ${
        compact ? "py-1.5 text-[11px]" : "text-xs"
      } ${
        active
          ? "border-cf-gold/40 bg-cf-active/50"
          : "border-cf-border-input bg-cf-card/40"
      }`}
    >
      <span className="font-medium text-cf-text">{name}</span>
      <span
        className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
          active
            ? "border-cf-gold/40 text-cf-gold"
            : "border-red-500/40 text-red-300"
        }`}
      >
        {active ? "Actif" : "En attente"}
      </span>
    </li>
  );
}
