import { API_PREFIX } from "@shared/constants";
import type { ProjectDetailResponse } from "@shared/types";
import { apiRequest } from "@/lib/api-client";
import { USD_TO_EUR } from "@/lib/dashboard-api";

export interface ProjectQuality {
  score: number;
  reviews_count: number;
  passed_all: boolean;
}

export interface ProjectLLMAgentCost {
  agent_name: string;
  cost_usd: number;
}

export interface ProjectLLMCost {
  total_cost_usd: number;
  total_tokens: number;
  by_agent: ProjectLLMAgentCost[];
}

export interface ProjectWorkflowSession {
  generation_id: string;
  workflow_id: string | null;
  status: string;
  agents_completed: number;
  total_agents: number;
  total_cost_usd: number | null;
  duration_ms: number | null;
  created_at: string;
}

export interface ProjectAuditEvent {
  event_type: string;
  event_data: Record<string, unknown>;
  actor_type: string;
  created_at: string;
}

function safeNumber(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function agentsCompletedCount(value: unknown): number {
  if (Array.isArray(value)) return value.length;
  return safeNumber(value);
}

function computeDurationMs(
  startedAt: unknown,
  completedAt: unknown,
): number | null {
  const start = typeof startedAt === "string" ? Date.parse(startedAt) : NaN;
  const end = typeof completedAt === "string" ? Date.parse(completedAt) : NaN;
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return null;
  }
  return end - start;
}

async function fetchProjectDetail(
  projectId: string,
): Promise<ProjectDetailResponse | null> {
  const res = await apiRequest<ProjectDetailResponse>({
    method: "GET",
    path: `${API_PREFIX}/projects/${encodeURIComponent(projectId)}`,
  });
  if (!res.ok) return null;
  return res.data;
}

export async function resolveLatestGenerationId(
  projectId: string,
  generationId?: string,
): Promise<string | null> {
  const explicit = generationId?.trim();
  if (explicit) return explicit;

  const detail = await fetchProjectDetail(projectId);
  const generations = detail?.generations ?? [];
  if (generations.length === 0) return null;
  return generations[0]?.id?.trim() || null;
}

export async function fetchProjectQuality(
  projectId: string,
  generationId?: string,
): Promise<ProjectQuality | null> {
  try {
    const gid = await resolveLatestGenerationId(projectId, generationId);
    if (!gid) return null;

    const res = await apiRequest<Record<string, unknown>>({
      method: "GET",
      path: `${API_PREFIX}/supervisor/quality/${encodeURIComponent(gid)}`,
    });
    if (!res.ok) return null;

    const payload = res.data ?? {};
    const score = safeNumber(payload.avg_score);
    return {
      score,
      reviews_count: safeNumber(payload.reviews_count),
      passed_all: Boolean(payload.passed_all),
    };
  } catch {
    return null;
  }
}

function normalizeWorkflowSession(
  row: Record<string, unknown>,
): ProjectWorkflowSession {
  const eventData =
    row.event_data && typeof row.event_data === "object" && !Array.isArray(row.event_data)
      ? (row.event_data as Record<string, unknown>)
      : {};

  const costFromEvent =
    eventData.cost_usd != null ? safeNumber(eventData.cost_usd) : null;

  return {
    generation_id: String(row.generation_id ?? ""),
    workflow_id: row.workflow_id != null ? String(row.workflow_id) : null,
    status: String(row.status ?? "unknown"),
    agents_completed: agentsCompletedCount(row.agents_completed),
    total_agents: safeNumber(row.total_agents),
    total_cost_usd: costFromEvent,
    duration_ms: computeDurationMs(row.started_at, row.completed_at),
    created_at: String(row.created_at ?? ""),
  };
}

export async function fetchProjectWorkflowHistory(
  projectId: string,
): Promise<ProjectWorkflowSession[]> {
  try {
    const res = await apiRequest<{ items?: unknown[] }>({
      method: "GET",
      path: `${API_PREFIX}/orchestration/sessions?project_id=${encodeURIComponent(projectId)}&limit=10`,
    });
    if (!res.ok) return [];

    const items = Array.isArray(res.data?.items) ? res.data.items : [];
    return items
      .map((row) => normalizeWorkflowSession(row as Record<string, unknown>))
      .filter((session) => session.generation_id);
  } catch {
    return [];
  }
}

function aggregateLLMUsage(items: unknown[]): ProjectLLMCost {
  const byAgent = new Map<string, number>();
  let totalCost = 0;
  let totalTokens = 0;

  for (const raw of items) {
    const row = raw as Record<string, unknown>;
    const agent = String(row.agent_name ?? "unknown").trim() || "unknown";
    const cost = safeNumber(row.cost_usd);
    const tokens = safeNumber(row.total_tokens ?? row.tokens);
    totalCost += cost;
    totalTokens += tokens;
    byAgent.set(agent, (byAgent.get(agent) ?? 0) + cost);
  }

  return {
    total_cost_usd: totalCost,
    total_tokens: totalTokens,
    by_agent: [...byAgent.entries()]
      .map(([agent_name, cost_usd]) => ({ agent_name, cost_usd }))
      .sort((a, b) => b.cost_usd - a.cost_usd),
  };
}

export async function fetchProjectLLMCost(
  projectId: string,
  generationId?: string,
): Promise<ProjectLLMCost | null> {
  try {
    const gid = await resolveLatestGenerationId(projectId, generationId);
    if (!gid) return null;

    const res = await apiRequest<{ items?: unknown[] }>({
      method: "GET",
      path: `${API_PREFIX}/llm-usage/generation/${encodeURIComponent(gid)}`,
    });
    if (!res.ok) return null;

    const items = Array.isArray(res.data?.items) ? res.data.items : [];
    return aggregateLLMUsage(items);
  } catch {
    return null;
  }
}

function normalizeAuditEvent(row: Record<string, unknown>): ProjectAuditEvent {
  const eventData = row.event_data;
  return {
    event_type: String(row.event_type ?? "unknown"),
    event_data:
      eventData && typeof eventData === "object" && !Array.isArray(eventData)
        ? (eventData as Record<string, unknown>)
        : {},
    actor_type: String(row.actor_type ?? "system"),
    created_at: String(row.created_at ?? ""),
  };
}

export async function fetchProjectAuditLog(
  projectId: string,
): Promise<ProjectAuditEvent[]> {
  try {
    const res = await apiRequest<{ items?: unknown[] }>({
      method: "GET",
      path: `${API_PREFIX}/audit/events?project_id=${encodeURIComponent(projectId)}&limit=20`,
    });
    if (!res.ok) return [];

    const items = Array.isArray(res.data?.items) ? res.data.items : [];
    return items.map((row) =>
      normalizeAuditEvent(row as Record<string, unknown>),
    );
  } catch {
    return [];
  }
}

export function formatCostEur(costUsd: number): string {
  const eur = costUsd * USD_TO_EUR;
  if (eur < 0.01 && costUsd > 0) return "< 0.01€";
  return `${eur.toFixed(2)}€`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms) || ms <= 0) return "—";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes <= 0) return `${seconds}s`;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

export function qualityBadgeVariant(
  score: number,
): "teal" | "amber" | "red" | "gray" {
  if (score >= 80) return "teal";
  if (score >= 60) return "amber";
  if (score > 0) return "red";
  return "gray";
}

export function workflowStatusVariant(
  status: string,
): "teal" | "amber" | "red" | "gray" {
  const normalized = status.toLowerCase();
  if (normalized === "completed") return "teal";
  if (normalized === "failed") return "red";
  if (normalized === "running" || normalized === "in_progress") return "amber";
  return "gray";
}

export function auditEventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    project_generated: "Site déployé",
    pipeline_planned: "Pipeline planifié",
    agent_model_updated: "Modèle modifié",
  };
  return labels[eventType] ?? eventType.replace(/_/g, " ");
}

export function auditEventIcon(eventType: string): string {
  const icons: Record<string, string> = {
    project_generated: "ti-rocket",
    pipeline_planned: "ti-route",
    agent_model_updated: "ti-settings",
  };
  return icons[eventType] ?? "ti-point";
}

export function formatRelativeTime(iso: string): string {
  const date = Date.parse(iso);
  if (!Number.isFinite(date)) return iso;
  const diffMs = date - Date.now();
  const rtf = new Intl.RelativeTimeFormat("fr", { numeric: "auto" });
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 1000 * 60 * 60 * 24 * 365],
    ["month", 1000 * 60 * 60 * 24 * 30],
    ["day", 1000 * 60 * 60 * 24],
    ["hour", 1000 * 60 * 60],
    ["minute", 1000 * 60],
    ["second", 1000],
  ];
  for (const [unit, unitMs] of units) {
    if (Math.abs(diffMs) >= unitMs || unit === "second") {
      return rtf.format(Math.round(diffMs / unitMs), unit);
    }
  }
  return iso;
}
