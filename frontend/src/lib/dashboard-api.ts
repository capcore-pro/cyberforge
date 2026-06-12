import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export interface LLMAgentCost {
  agent: string;
  cost_usd: number;
  tokens: number;
}

export interface LLMMonthlyStats {
  total_cost_usd: number;
  total_tokens: number;
  by_agent: LLMAgentCost[];
}

export interface LLMDailyPoint {
  date: string;
  cost_usd: number;
  tokens: number;
}

export interface LLMStats {
  monthly: LLMMonthlyStats;
  daily: LLMDailyPoint[];
}

export interface SupervisorStats {
  days?: number;
  total_validations: number;
  pass_rate: number;
  avg_quality_score: number;
  avg_attempts: number;
}

export interface OrchestrationSession {
  generation_id: string;
  workflow_id: string | null;
  project_id: string | null;
  status: string;
  agents_completed: number;
  total_agents: number;
  created_at: string;
}

export interface AuditGenerationEvent {
  id?: string;
  project_id?: string | null;
  event_data: Record<string, unknown>;
  created_at: string;
}

export interface MergedGenerationEntry {
  generationId: string;
  status: string;
  agentsCompleted: number;
  totalAgents: number;
  createdAt: string;
  clientName: string;
  projectType: string;
  qualityScore: number | null;
  costUsd: number | null;
}

const EMPTY_LLM_STATS: LLMStats = {
  monthly: { total_cost_usd: 0, total_tokens: 0, by_agent: [] },
  daily: [],
};

const EMPTY_SUPERVISOR_STATS: SupervisorStats = {
  total_validations: 0,
  pass_rate: 0,
  avg_quality_score: 0,
  avg_attempts: 0,
};

function safeNumber(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function normalizeLLMStats(data: unknown): LLMStats {
  const payload = (data ?? {}) as Record<string, unknown>;
  const monthlyRaw = (payload.monthly ?? {}) as Record<string, unknown>;
  const byAgentRaw = Array.isArray(monthlyRaw.by_agent) ? monthlyRaw.by_agent : [];
  const dailyRaw = Array.isArray(payload.daily) ? payload.daily : [];

  return {
    monthly: {
      total_cost_usd: safeNumber(monthlyRaw.total_cost_usd),
      total_tokens: safeNumber(monthlyRaw.total_tokens),
      by_agent: byAgentRaw.map((row) => {
        const item = row as Record<string, unknown>;
        return {
          agent: String(item.agent ?? "unknown"),
          cost_usd: safeNumber(item.cost_usd),
          tokens: safeNumber(item.tokens),
        };
      }),
    },
    daily: dailyRaw.map((row) => {
      const item = row as Record<string, unknown>;
      return {
        date: String(item.date ?? ""),
        cost_usd: safeNumber(item.cost_usd),
        tokens: safeNumber(item.tokens),
      };
    }),
  };
}

function normalizeSupervisorStats(data: unknown): SupervisorStats {
  const payload = (data ?? {}) as Record<string, unknown>;
  return {
    days: payload.days != null ? safeNumber(payload.days) : undefined,
    total_validations: safeNumber(payload.total_validations),
    pass_rate: safeNumber(payload.pass_rate),
    avg_quality_score: safeNumber(payload.avg_quality_score),
    avg_attempts: safeNumber(payload.avg_attempts),
  };
}

function normalizeSession(row: Record<string, unknown>): OrchestrationSession {
  return {
    generation_id: String(row.generation_id ?? ""),
    workflow_id: row.workflow_id != null ? String(row.workflow_id) : null,
    project_id: row.project_id != null ? String(row.project_id) : null,
    status: String(row.status ?? "unknown"),
    agents_completed: safeNumber(row.agents_completed),
    total_agents: safeNumber(row.total_agents),
    created_at: String(row.created_at ?? ""),
  };
}

function normalizeAuditEvent(row: Record<string, unknown>): AuditGenerationEvent {
  const eventData = row.event_data;
  return {
    id: row.id != null ? String(row.id) : undefined,
    project_id: row.project_id != null ? String(row.project_id) : null,
    event_data:
      eventData && typeof eventData === "object" && !Array.isArray(eventData)
        ? (eventData as Record<string, unknown>)
        : {},
    created_at: String(row.created_at ?? ""),
  };
}

export async function fetchLLMStats(): Promise<LLMStats> {
  const res = await apiRequest<LLMStats>({
    method: "GET",
    path: `${API_PREFIX}/stats/llm`,
  });
  if (!res.ok) {
    console.warn(apiErrorMessage(res, "Impossible de charger les stats LLM."));
    return EMPTY_LLM_STATS;
  }
  return normalizeLLMStats(res.data);
}

export async function fetchSupervisorStats(): Promise<SupervisorStats> {
  const res = await apiRequest<SupervisorStats>({
    method: "GET",
    path: `${API_PREFIX}/supervisor/stats`,
  });
  if (!res.ok) {
    console.warn(apiErrorMessage(res, "Impossible de charger les stats supervisor."));
    return EMPTY_SUPERVISOR_STATS;
  }
  return normalizeSupervisorStats(res.data);
}

export async function fetchRecentSessions(
  limit = 5,
): Promise<OrchestrationSession[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/orchestration/sessions?limit=${limit}`,
  });
  if (!res.ok) {
    console.warn(apiErrorMessage(res, "Impossible de charger les sessions."));
    return [];
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) =>
    normalizeSession(row as Record<string, unknown>),
  );
}

export async function fetchRecentGenerations(
  limit = 5,
): Promise<AuditGenerationEvent[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/audit/events?event_type=project_generated&limit=${limit}`,
  });
  if (!res.ok) {
    console.warn(apiErrorMessage(res, "Impossible de charger les générations."));
    return [];
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) =>
    normalizeAuditEvent(row as Record<string, unknown>),
  );
}

/** Fusionne sessions orchestration et événements audit par generation_id / project_id. */
export function mergeGenerationEntries(
  sessions: OrchestrationSession[],
  generations: AuditGenerationEvent[],
): MergedGenerationEntry[] {
  const auditByGeneration = new Map<string, AuditGenerationEvent>();
  const auditByProject = new Map<string, AuditGenerationEvent>();

  for (const event of generations) {
    const data = event.event_data ?? {};
    const gid = String(data.generation_id ?? "").trim();
    if (gid) {
      auditByGeneration.set(gid, event);
    }
    const pid = String(event.project_id ?? data.project_id ?? "").trim();
    if (pid && !auditByProject.has(pid)) {
      auditByProject.set(pid, event);
    }
  }

  const fromSessions = sessions
    .filter((s) => s.generation_id)
    .map((session) => {
      const audit =
        auditByGeneration.get(session.generation_id) ??
        (session.project_id
          ? auditByProject.get(session.project_id)
          : undefined);
      const data = audit?.event_data ?? {};
      return {
        generationId: session.generation_id,
        status: session.status,
        agentsCompleted: session.agents_completed,
        totalAgents: session.total_agents,
        createdAt: session.created_at || audit?.created_at || "",
        clientName: String(data.client_name ?? "Projet sans nom"),
        projectType: String(data.project_type ?? ""),
        qualityScore:
          data.quality_score != null ? safeNumber(data.quality_score) : null,
        costUsd: data.cost_usd != null ? safeNumber(data.cost_usd) : null,
      };
    });

  if (fromSessions.length > 0) {
    return fromSessions
      .sort(
        (a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      )
      .slice(0, 5);
  }

  return generations
    .map((event) => {
      const data = event.event_data ?? {};
      const gid = String(data.generation_id ?? event.id ?? "").trim();
      return {
        generationId: gid || `audit-${event.created_at}`,
        status: "completed",
        agentsCompleted: 0,
        totalAgents: 0,
        createdAt: event.created_at,
        clientName: String(data.client_name ?? "Projet sans nom"),
        projectType: String(data.project_type ?? ""),
        qualityScore:
          data.quality_score != null ? safeNumber(data.quality_score) : null,
        costUsd: data.cost_usd != null ? safeNumber(data.cost_usd) : null,
      };
    })
    .slice(0, 5);
}

export const USD_TO_EUR = 0.92;
