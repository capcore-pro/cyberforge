import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { API_PREFIX } from "@shared/constants";
import type { AgentsStatusResponse } from "@shared/types";
import { apiRequest } from "@/lib/api-client";
import { SECRETS_SAVED_EVENT } from "@/lib/secrets-events";
import { useBackendHealth } from "@/context/BackendHealthContext";

export type AgentDisplayStatus = "active" | "standby";

interface AgentsStatusContextValue {
  status: AgentsStatusResponse | null;
  /** True après au moins une réponse API réussie (session courante). */
  agentsCountKnown: boolean;
  loading: boolean;
  refresh: () => Promise<void>;
  getAgentStatus: (agentId: string) => AgentDisplayStatus;
  /** Nombre d'agents actifs — `null` tant que l'API n'a pas répondu. */
  activeCount: number | null;
  totalAgents: number;
}

const AgentsStatusContext = createContext<AgentsStatusContextValue | null>(null);

const POLL_MS = 15_000;

/** Pipeline v2 — aligné sur GET /api/agents/status (8 agents). */
const PIPELINE_AGENT_IDS = [
  "brief",
  "supervisor",
  "generator",
  "deploy",
  "database",
  "auth",
  "payment",
  "electron",
] as const;

/** Affichage sidebar — distingue chargement, inconnu et compte réel. */
export function formatAgentsCountDisplay({
  activeCount,
  totalAgents,
  agentsCountKnown,
  loading,
}: {
  activeCount: number | null;
  totalAgents: number;
  agentsCountKnown: boolean;
  loading: boolean;
}): string {
  if (agentsCountKnown && activeCount !== null) {
    return `${activeCount} / ${totalAgents}`;
  }
  if (loading) return `… / ${totalAgents}`;
  return `— / ${totalAgents}`;
}

/** Badge dashboard — libellé selon backend + disponibilité API agents. */
export function formatAgentsBadgeLabel({
  backendOnline,
  activeCount,
  totalAgents,
  agentsCountKnown,
  loading,
}: {
  backendOnline: boolean;
  activeCount: number | null;
  totalAgents: number;
  agentsCountKnown: boolean;
  loading: boolean;
}): string {
  if (!backendOnline) return "Backend hors ligne";
  if (agentsCountKnown && activeCount !== null) {
    return `${activeCount}/${totalAgents} agents actifs`;
  }
  if (loading) return "Chargement agents…";
  return "Statut agents indisponible";
}

export function AgentsStatusProvider({ children }: { children: ReactNode }) {
  const { status: backendStatus } = useBackendHealth();
  const [data, setData] = useState<AgentsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (backendStatus !== "online") {
      setLoading(backendStatus === "loading");
      return;
    }
    setLoading(true);
    try {
      const response = await apiRequest<AgentsStatusResponse>({
        method: "GET",
        path: `${API_PREFIX}/agents/status`,
        timeoutMs: 8000,
      });
      if (response.ok && response.data) {
        setData(response.data);
      }
    } catch {
      // Conserve la dernière valeur connue ; sinon l'UI affiche —/8.
    } finally {
      setLoading(false);
    }
  }, [backendStatus]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    const onSecretsSaved = () => void refresh();
    window.addEventListener(SECRETS_SAVED_EVENT, onSecretsSaved);
    return () => window.removeEventListener(SECRETS_SAVED_EVENT, onSecretsSaved);
  }, [refresh]);

  const getAgentStatus = useCallback(
    (agentId: string): AgentDisplayStatus => {
      const item = data?.agents.find((a) => a.id === agentId);
      if (!item) return "standby";
      return item.status === "active" ? "active" : "standby";
    },
    [data],
  );

  const agentsCountKnown = data !== null;

  const value = useMemo(
    () => ({
      status: data,
      agentsCountKnown,
      loading,
      refresh,
      getAgentStatus,
      activeCount: agentsCountKnown ? (data?.active_count ?? null) : null,
      totalAgents: data?.total_agents ?? PIPELINE_AGENT_IDS.length,
    }),
    [data, agentsCountKnown, loading, refresh, getAgentStatus],
  );

  return (
    <AgentsStatusContext.Provider value={value}>
      {children}
    </AgentsStatusContext.Provider>
  );
}

export function useAgentsStatus(): AgentsStatusContextValue {
  const ctx = useContext(AgentsStatusContext);
  if (!ctx) {
    throw new Error(
      "useAgentsStatus doit être utilisé dans AgentsStatusProvider",
    );
  }
  return ctx;
}
