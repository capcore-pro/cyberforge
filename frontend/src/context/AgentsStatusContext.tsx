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
import { useBackendHealth } from "@/context/BackendHealthContext";

export type AgentDisplayStatus = "active" | "standby";

interface AgentsStatusContextValue {
  status: AgentsStatusResponse | null;
  loading: boolean;
  refresh: () => Promise<void>;
  getAgentStatus: (agentId: string) => AgentDisplayStatus;
  activeCount: number;
  totalAgents: number;
}

const AgentsStatusContext = createContext<AgentsStatusContextValue | null>(null);

const POLL_MS = 15_000;

const PIPELINE_AGENT_IDS = [
  "architect",
  "builder",
  "coremind",
  "bughunter",
  "autofix",
] as const;

const AGENT_CATALOG: { id: string; name: string; description: string }[] = [
  {
    id: "coremind",
    name: "CoreMindAI",
    description: "Orchestrateur central du pipeline LangGraph.",
  },
  {
    id: "architect",
    name: "ArchitectAI",
    description: "Analyse du prompt et choix du template premium.",
  },
  {
    id: "builder",
    name: "BuilderAI",
    description: "Génération de code et scaffolding de modules.",
  },
  {
    id: "bughunter",
    name: "BugHunterAI",
    description: "Vérification du HTML généré avant livraison.",
  },
  {
    id: "autofix",
    name: "AutoFixAI",
    description: "Correction automatique des livrables défectueux.",
  },
  {
    id: "visionui",
    name: "VisionUI",
    description: "Interfaces visuelles et design system cyber.",
  },
  {
    id: "testpilot",
    name: "TestPilotAI",
    description: "Tests automatisés et validation de régression.",
  },
  {
    id: "export",
    name: "ExportAI",
    description: "Export de rapports et documentation client.",
  },
];

/** Aligné sur GET /api/agents/status — affiché tant que l'API n'a pas répondu. */
function defaultAgentsStatus(): AgentsStatusResponse {
  const pipelineSet = new Set<string>(PIPELINE_AGENT_IDS);
  return {
    total_agents: AGENT_CATALOG.length,
    active_count: PIPELINE_AGENT_IDS.length,
    pipeline_agent_ids: [...PIPELINE_AGENT_IDS],
    agents: AGENT_CATALOG.map(({ id, name, description }) => ({
      id,
      name,
      description,
      status: pipelineSet.has(id) ? "active" : "standby",
      in_pipeline: pipelineSet.has(id),
    })),
  };
}

const DEFAULT_AGENTS_STATUS = defaultAgentsStatus();

export function AgentsStatusProvider({ children }: { children: ReactNode }) {
  const { status: backendStatus } = useBackendHealth();
  const [data, setData] = useState<AgentsStatusResponse | null>(
    DEFAULT_AGENTS_STATUS,
  );
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (backendStatus !== "online") {
      setData(DEFAULT_AGENTS_STATUS);
      setLoading(false);
      return;
    }
    try {
      const response = await apiRequest<AgentsStatusResponse>({
        method: "GET",
        path: `${API_PREFIX}/agents/status`,
        timeoutMs: 8000,
      });
      if (response.ok && response.data) {
        setData(response.data);
      } else {
        setData(DEFAULT_AGENTS_STATUS);
      }
    } catch {
      setData(DEFAULT_AGENTS_STATUS);
    } finally {
      setLoading(false);
    }
  }, [backendStatus]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const getAgentStatus = useCallback(
    (agentId: string): AgentDisplayStatus => {
      const item = data?.agents.find((a) => a.id === agentId);
      if (!item) return "standby";
      return item.status === "active" ? "active" : "standby";
    },
    [data],
  );

  const value = useMemo(
    () => ({
      status: data,
      loading,
      refresh,
      getAgentStatus,
      activeCount: data?.active_count ?? DEFAULT_AGENTS_STATUS.active_count,
      totalAgents: data?.total_agents ?? DEFAULT_AGENTS_STATUS.total_agents,
    }),
    [data, loading, refresh, getAgentStatus],
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
