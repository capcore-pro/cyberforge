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
  loading: boolean;
  refresh: () => Promise<void>;
  getAgentStatus: (agentId: string) => AgentDisplayStatus;
  activeCount: number;
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

const AGENT_CATALOG: { id: string; name: string; description: string }[] = [
  {
    id: "brief",
    name: "BriefAI",
    description: "Brief structuré + Firecrawl (concurrents).",
  },
  {
    id: "supervisor",
    name: "SupervisorAI",
    description: "Validation binaire à chaque étape du pipeline.",
  },
  {
    id: "generator",
    name: "GeneratorAI",
    description: "HTML complet en un appel Claude.",
  },
  {
    id: "deploy",
    name: "DeployAI",
    description: "Images Pexels + déploiement Cloudflare Pages.",
  },
  {
    id: "database",
    name: "DatabaseAI",
    description: "Schéma Supabase si app / ecommerce / réservation.",
  },
  {
    id: "auth",
    name: "AuthAI",
    description: "Auth Supabase si application web.",
  },
  {
    id: "payment",
    name: "PaymentAI",
    description: "Stripe si ecommerce / réservation.",
  },
  {
    id: "electron",
    name: "ElectronAI",
    description: "Empaquetage application desktop (.exe).",
  },
];

const KEYLESS_PIPELINE_AGENTS = new Set([
  "supervisor",
  "deploy",
  "electron",
]);

function defaultAgentsStatus(): AgentsStatusResponse {
  const pipelineSet = new Set<string>(PIPELINE_AGENT_IDS);
  let active_count = 0;
  const agents = AGENT_CATALOG.map(({ id, name, description }) => {
    const in_pipeline = pipelineSet.has(id);
    const is_active = in_pipeline && KEYLESS_PIPELINE_AGENTS.has(id);
    if (is_active) active_count += 1;
    return {
      id,
      name,
      description,
      status: (is_active ? "active" : "standby") as "active" | "standby",
      in_pipeline,
    };
  });
  return {
    total_agents: PIPELINE_AGENT_IDS.length,
    active_count,
    pipeline_agent_ids: [...PIPELINE_AGENT_IDS],
    agents,
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
