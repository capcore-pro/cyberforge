import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export interface AgentRegistryEntry {
  agent_id: string;
  name: string;
  slug: string;
  category: string;
  description: string;
  version: string;
  provider: string | null;
  model: string | null;
  capabilities: string[];
  system_prompt_slug: string | null;
  enabled: boolean;
  in_pipeline: boolean;
  requires_key: string | null;
}

export interface AgentStatusEntry {
  id: string;
  name: string;
  description: string;
  active: boolean;
  source: "registry" | "fallback";
  category?: string;
  model?: string;
  provider?: string;
}

export interface AgentMetrics {
  total_executions: number;
  success_count: number;
  failure_count: number;
  avg_duration_ms: number;
  total_cost: number;
}

interface RegistryListResponse {
  items?: AgentRegistryEntry[];
  count?: number;
}

function normalizeCapabilities(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map((item) => String(item));
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item));
      }
    } catch {
      return [];
    }
  }
  return [];
}

export function normalizeAgentRegistryEntry(
  row: Record<string, unknown>,
): AgentRegistryEntry {
  return {
    agent_id: String(row.agent_id ?? ""),
    name: String(row.name ?? ""),
    slug: String(row.slug ?? ""),
    category: String(row.category ?? "general"),
    description: String(row.description ?? ""),
    version: String(row.version ?? "1.0.0"),
    provider: row.provider != null ? String(row.provider) : null,
    model: row.model != null ? String(row.model) : null,
    capabilities: normalizeCapabilities(row.capabilities),
    system_prompt_slug:
      row.system_prompt_slug != null ? String(row.system_prompt_slug) : null,
    enabled: Boolean(row.enabled),
    in_pipeline: Boolean(row.in_pipeline),
    requires_key: row.requires_key != null ? String(row.requires_key) : null,
  };
}

function unwrapRegistryList(data: unknown): AgentRegistryEntry[] {
  if (Array.isArray(data)) {
    return data.map((row) =>
      normalizeAgentRegistryEntry(row as Record<string, unknown>),
    );
  }
  const payload = data as RegistryListResponse;
  const items = payload?.items ?? [];
  return items.map((row) =>
    normalizeAgentRegistryEntry(row as unknown as Record<string, unknown>),
  );
}

export async function fetchAgentRegistry(): Promise<AgentRegistryEntry[]> {
  const res = await apiRequest<RegistryListResponse | AgentRegistryEntry[]>({
    method: "GET",
    path: `${API_PREFIX}/agents/registry`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger le registre agents."));
  }
  return unwrapRegistryList(res.data);
}

export async function fetchPipelineAgents(): Promise<AgentRegistryEntry[]> {
  const res = await apiRequest<RegistryListResponse | AgentRegistryEntry[]>({
    method: "GET",
    path: `${API_PREFIX}/agents/registry/pipeline`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les agents pipeline."));
  }
  return unwrapRegistryList(res.data);
}

export async function fetchAgentDetail(
  agentId: string,
): Promise<AgentRegistryEntry> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/agents/registry/${encodeURIComponent(agentId)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Agent introuvable."));
  }
  return normalizeAgentRegistryEntry(res.data ?? {});
}

export async function updateAgentModel(
  agentId: string,
  model: string,
  provider: string,
): Promise<AgentRegistryEntry> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "PATCH",
    path: `${API_PREFIX}/agents/registry/${encodeURIComponent(agentId)}/model`,
    body: { model, provider },
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Mise à jour du modèle impossible."));
  }
  return normalizeAgentRegistryEntry(res.data ?? {});
}

export async function toggleAgent(
  agentId: string,
  enabled: boolean,
): Promise<AgentRegistryEntry> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "PATCH",
    path: `${API_PREFIX}/agents/registry/${encodeURIComponent(agentId)}/enable`,
    body: { enabled },
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Mise à jour du statut impossible."));
  }
  return normalizeAgentRegistryEntry(res.data ?? {});
}

export async function fetchAgentMetrics(agentId: string): Promise<AgentMetrics> {
  const res = await apiRequest<AgentMetrics>({
    method: "GET",
    path: `${API_PREFIX}/agents/registry/${encodeURIComponent(agentId)}/metrics`,
  });
  if (!res.ok) {
    return {
      total_executions: 0,
      success_count: 0,
      failure_count: 0,
      avg_duration_ms: 0,
      total_cost: 0,
    };
  }
  const data = res.data ?? ({} as AgentMetrics);
  return {
    total_executions: Number(data.total_executions ?? 0),
    success_count: Number(data.success_count ?? 0),
    failure_count: Number(data.failure_count ?? 0),
    avg_duration_ms: Number(data.avg_duration_ms ?? 0),
    total_cost: Number(data.total_cost ?? 0),
  };
}

export const PROVIDER_MODELS: Record<string, string[]> = {
  anthropic: [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5",
    "claude-opus-4-6",
  ],
  openai: ["gpt-4o", "gpt-4o-mini"],
  deepseek: ["deepseek-chat"],
  ollama: ["qwen3", "llama3.2"],
};

export function sortAgents(entries: AgentRegistryEntry[]): AgentRegistryEntry[] {
  return [...entries].sort((a, b) => {
    if (a.in_pipeline !== b.in_pipeline) {
      return a.in_pipeline ? -1 : 1;
    }
    const cat = a.category.localeCompare(b.category, "fr");
    if (cat !== 0) return cat;
    return a.name.localeCompare(b.name, "fr");
  });
}
