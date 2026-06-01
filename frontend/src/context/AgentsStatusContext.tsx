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

const PIPELINE_AGENT_IDS = [
  "architect",
  "research",
  "stitch",
  "openhands",
  "builder",
  "coremind",
  "visionui",
  "bughunter",
  "autofix",
  "testpilot",
  "playwright",
  "lighthouse",
  "export",
] as const;

const AGENT_CATALOG: { id: string; name: string; description: string }[] = [
  {
    id: "architect",
    name: "ArchitectAI",
    description: "Analyse du prompt et choix du template premium.",
  },
  {
    id: "research",
    name: "ResearchAI",
    description: "Recherche Brave Search + Exa AI (secteur, concurrents).",
  },
  {
    id: "stitch",
    name: "StitchAI",
    description: "Maquettes visuelles HTML + screenshots (Google Stitch).",
  },
  {
    id: "openhands",
    name: "OpenHands",
    description: "Génération de code avancée pour projets complexes.",
  },
  {
    id: "builder",
    name: "BuilderAI",
    description: "Génération v0 / DeepSeek avec référence Stitch.",
  },
  {
    id: "coremind",
    name: "CoreMindAI",
    description: "Orchestrateur central du pipeline LangGraph.",
  },
  {
    id: "visionui",
    name: "VisionUI",
    description: "Interfaces visuelles et design system cyber.",
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
    id: "testpilot",
    name: "TestPilotAI",
    description: "Tests automatisés et validation de régression.",
  },
  {
    id: "playwright",
    name: "Playwright",
    description: "Tests E2E Chromium headless.",
  },
  {
    id: "lighthouse",
    name: "Lighthouse",
    description: "Audit Performance, SEO, accessibilité.",
  },
  {
    id: "export",
    name: "ExportAI",
    description: "Export et déploiement Cloudflare / Railway.",
  },
];

const KEYLESS_PIPELINE_AGENTS = new Set([
  "architect",
  "bughunter",
  "autofix",
  "testpilot",
  "playwright",
  "lighthouse",
  "export",
]);

/** 13 agents — aligné sur GET /api/agents/status (repli hors ligne) */
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
    total_agents: AGENT_CATALOG.length,
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
