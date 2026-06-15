import { useAppStore } from "./store";

export const DEFAULT_BASE_URL = "http://127.0.0.1:8002";

export function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) {
    return DEFAULT_BASE_URL;
  }
  return trimmed.replace(/\/+$/, "");
}

export function getBaseUrl(): string {
  return normalizeBaseUrl(useAppStore.getState().baseUrl || DEFAULT_BASE_URL);
}

export async function testBackendConnection(url: string): Promise<void> {
  const baseUrl = normalizeBaseUrl(url);
  const res = await fetch(`${baseUrl}/api/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
}

export async function apiCall<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const baseUrl = getBaseUrl();
  const res = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export const fetchDashboard = () =>
  Promise.all([
    apiCall<Project[]>("/api/projects?limit=5"),
    apiCall<AgentsStatus>("/api/agents/status"),
    apiCall<LlmStats>("/api/stats/llm"),
    apiCall<SupervisorStats>("/api/supervisor/stats"),
    apiCall<MonitoringHealth>("/api/monitoring/health"),
  ] as const);

export const fetchProjects = () => apiCall<Project[]>("/api/projects");

export const fetchProspects = (statut?: string) =>
  apiCall<Prospect[]>(
    `/api/pipeline/prospects${statut ? `?statut=${encodeURIComponent(statut)}` : ""}`,
  );

export const moveProspect = (id: string, statut: string) =>
  apiCall<Prospect>(`/api/pipeline/prospects/${id}/statut`, {
    method: "PATCH",
    body: JSON.stringify({ statut }),
  });

export const createProspect = (body: {
  nom: string;
  entreprise?: string;
  email?: string;
}) =>
  apiCall<Prospect>("/api/pipeline/prospects", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const fetchAlerts = () =>
  apiCall<AlertsResponse>("/api/monitoring/alerts?status=open");

export const fetchHealth = () => apiCall<{ status?: string }>("/api/health");

export const fetchMonitoringHealth = () =>
  apiCall<MonitoringHealth>("/api/monitoring/health");

export const acknowledgeAlert = (id: string) =>
  apiCall(`/api/monitoring/alerts/${id}/acknowledge`, { method: "POST" });

export const runMonitoringCheck = () =>
  apiCall("/api/monitoring/check", { method: "POST" });

export const fetchAuditEvents = (eventType: string, limit = 3) =>
  apiCall<AuditEventsResponse>(
    `/api/audit/events?event_type=${encodeURIComponent(eventType)}&limit=${limit}`,
  );

export const registerPushToken = (token: string, platform = "android") =>
  apiCall("/api/mobile/register-push-token", {
    method: "POST",
    body: JSON.stringify({ token, platform }),
  });

export const fetchMobileHealth = () =>
  apiCall<{ status: string; tokens: number }>("/api/mobile/health");

export interface Project {
  id: string;
  title: string;
  prompt: string;
  project_type: string;
  created_at: string;
  demo_url?: string | null;
  generation_count?: number;
  latest_estimated_cost_usd?: number | null;
}

export interface AgentsStatus {
  total_agents: number;
  active_count: number;
  agents: Array<{ id: string; name: string; status: string }>;
}

export interface LlmStats {
  monthly?: { total_cost_usd?: number };
}

export interface SupervisorStats {
  pass_rate?: number;
  total_validations?: number;
}

export interface MonitoringHealth {
  overall_status?: string;
  api?: { status?: string; latency_ms?: number };
  agents?: { active?: number; total?: number };
  pipeline?: { pass_rate?: number };
  costs?: { month_usd?: number; today_usd?: number };
}

export interface Prospect {
  id: string;
  nom: string;
  entreprise?: string | null;
  email?: string | null;
  statut: string;
  valeur_estimee?: number;
  created_at?: string;
}

export interface Alert {
  id: string;
  title?: string;
  message?: string;
  severity?: string;
  source?: string;
  status?: string;
  created_at?: string;
}

export interface AlertsResponse {
  items: Alert[];
  count: number;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  created_at?: string;
  payload?: Record<string, unknown>;
}

export interface AuditEventsResponse {
  items: AuditEvent[];
  count: number;
}
