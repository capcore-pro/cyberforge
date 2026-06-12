import { useCallback, useEffect, useMemo, useState } from "react";
import { AgentCard } from "@/components/agents/AgentCard";
import { AgentDetailModal } from "@/components/agents/AgentDetailModal";
import { GHOST_BTN, TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import { formatAgentsCountDisplay, useAgentsStatus } from "@/context/AgentsStatusContext";
import {
  fetchAgentRegistry,
  sortAgents,
  type AgentRegistryEntry,
} from "@/lib/agents-api";
import { fetchSecretsStatus, type VaultConfiguredFlags } from "@/lib/secrets-api";
import { isKeyConfigured } from "@/components/agents/agent-ui";

type AgentsTab = "pipeline" | "all";

export function AgentsPage() {
  const {
    activeCount,
    totalAgents,
    agentsCountKnown,
    loading: statusLoading,
    refresh,
    status,
  } = useAgentsStatus();

  const [tab, setTab] = useState<AgentsTab>("pipeline");
  const [agents, setAgents] = useState<AgentRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<AgentRegistryEntry | null>(null);
  const [secretsConfigured, setSecretsConfigured] = useState<
    VaultConfiguredFlags | undefined
  >();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [registry, secretsRes] = await Promise.all([
        fetchAgentRegistry(),
        fetchSecretsStatus(),
      ]);
      setAgents(sortAgents(registry));
      if (secretsRes.ok && secretsRes.data?.configured) {
        setSecretsConfigured(secretsRes.data.configured);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const statusMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of status?.agents ?? []) {
      map.set(item.id, item.status);
    }
    return map;
  }, [status]);

  const filtered = useMemo(() => {
    const list =
      tab === "pipeline" ? agents.filter((a) => a.in_pipeline) : agents;
    return sortAgents(list);
  }, [agents, tab]);

  const badgeLabel = formatAgentsCountDisplay({
    activeCount,
    totalAgents,
    agentsCountKnown,
    loading: statusLoading,
  });

  function handleAgentUpdated(updated: AgentRegistryEntry) {
    setAgents((prev) =>
      sortAgents(
        prev.map((item) =>
          item.agent_id === updated.agent_id ? updated : item,
        ),
      ),
    );
    setSelected(updated);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
            <i className="ti ti-robot text-base" aria-hidden />
            Orchestration IA
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-white">
            <i className="ti ti-robot text-[#d4a843]" aria-hidden />
            Agents IA
          </h1>
          <p className="mt-2 text-sm text-white/50">
            Registre officiel, modèles par défaut et statut runtime du pipeline v2.
          </p>
        </div>
        <span className="rounded-full border border-[#d4a843]/35 bg-[#d4a843]/10 px-3 py-1 text-xs font-semibold text-[#d4a843]">
          {badgeLabel} agents actifs
        </span>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setTab("pipeline")}
            className={`${TAB_BASE} rounded-control ${tab === "pipeline" ? TAB_ACTIVE : ""}`}
          >
            Pipeline
          </button>
          <button
            type="button"
            onClick={() => setTab("all")}
            className={`${TAB_BASE} rounded-control ${tab === "all" ? TAB_ACTIVE : ""}`}
          >
            Tous les agents
          </button>
        </nav>
        <button
          type="button"
          onClick={() => {
            void load();
            void refresh();
          }}
          className={`${GHOST_BTN} inline-flex items-center gap-2`}
        >
          <i className="ti ti-refresh" aria-hidden />
          Actualiser
        </button>
      </div>

      {error ? (
        <div className="rounded-control border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="flex min-h-[240px] items-center justify-center">
          <i
            className="ti ti-loader-2 animate-spin text-3xl text-[#d4a843]"
            aria-label="Chargement"
          />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 text-center text-white/50">
          <i className="ti ti-robot-off text-4xl text-white/25" aria-hidden />
          <p>Aucun agent à afficher pour cet onglet.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              statusMap={statusMap}
              keyConfigured={isKeyConfigured(
                agent.requires_key,
                secretsConfigured,
              )}
              onOpenDetails={setSelected}
            />
          ))}
        </div>
      )}

      <AgentDetailModal
        agent={selected}
        open={selected != null}
        secretsConfigured={secretsConfigured}
        onClose={() => setSelected(null)}
        onUpdated={handleAgentUpdated}
      />
    </div>
  );
}
