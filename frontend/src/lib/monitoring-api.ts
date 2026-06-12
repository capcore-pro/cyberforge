import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export type OverallStatus = "healthy" | "degraded" | "critical";

export interface MonitoringHealth {
  overall_status: OverallStatus;
  api: { status: string; latency_ms: number };
  agents: { active: number; total: number };
  pipeline: {
    pass_rate: number;
    avg_quality_score: number;
    days: number;
  };
  costs: { today_usd: number; month_usd: number };
}

export interface MonitoringAlert {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string | null;
  source: string | null;
  source_id: string | null;
  status: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface MonitoringIncident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  source: string | null;
  alert_id: string | null;
  detected_at: string;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
}

export interface MonitoringCheckResult {
  created: MonitoringAlert[];
  skipped: string[];
  metrics: Record<string, number>;
  error?: string;
}

const EMPTY_HEALTH: MonitoringHealth = {
  overall_status: "healthy",
  api: { status: "offline", latency_ms: 0 },
  agents: { active: 0, total: 0 },
  pipeline: { pass_rate: 0, avg_quality_score: 0, days: 30 },
  costs: { today_usd: 0, month_usd: 0 },
};

function normalizeAlert(row: Record<string, unknown>): MonitoringAlert {
  return {
    id: String(row.id ?? ""),
    alert_type: String(row.alert_type ?? ""),
    severity: String(row.severity ?? "warning"),
    title: String(row.title ?? ""),
    message: row.message != null ? String(row.message) : null,
    source: row.source != null ? String(row.source) : null,
    source_id: row.source_id != null ? String(row.source_id) : null,
    status: String(row.status ?? "open"),
    acknowledged_at:
      row.acknowledged_at != null ? String(row.acknowledged_at) : null,
    resolved_at: row.resolved_at != null ? String(row.resolved_at) : null,
    created_at: String(row.created_at ?? ""),
  };
}

function normalizeIncident(row: Record<string, unknown>): MonitoringIncident {
  return {
    id: String(row.id ?? ""),
    title: String(row.title ?? ""),
    description: row.description != null ? String(row.description) : null,
    severity: String(row.severity ?? "medium"),
    status: String(row.status ?? "open"),
    source: row.source != null ? String(row.source) : null,
    alert_id: row.alert_id != null ? String(row.alert_id) : null,
    detected_at: String(row.detected_at ?? row.created_at ?? ""),
    resolved_at: row.resolved_at != null ? String(row.resolved_at) : null,
    resolution_notes:
      row.resolution_notes != null ? String(row.resolution_notes) : null,
    created_at: String(row.created_at ?? ""),
  };
}

export async function fetchMonitoringHealth(): Promise<MonitoringHealth> {
  const res = await apiRequest<MonitoringHealth>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/health`,
  });
  if (!res.ok) {
    console.warn(apiErrorMessage(res, "Health monitoring indisponible."));
    return EMPTY_HEALTH;
  }
  return { ...EMPTY_HEALTH, ...(res.data ?? {}) };
}

export async function fetchMonitoringAlerts(opts?: {
  status?: string;
  severity?: string;
}): Promise<MonitoringAlert[]> {
  const params = new URLSearchParams({ limit: "50" });
  if (opts?.status && opts.status !== "all") {
    params.set("status", opts.status);
  } else if (!opts?.status) {
    params.set("status", "open");
  }
  if (opts?.severity) {
    params.set("severity", opts.severity);
  }
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/alerts?${params.toString()}`,
  });
  if (!res.ok) {
    return [];
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) => normalizeAlert(row as Record<string, unknown>));
}

export async function fetchMonitoringIncidents(
  status?: string,
): Promise<MonitoringIncident[]> {
  const qs = status
    ? `?status=${encodeURIComponent(status)}&limit=50`
    : "?limit=50";
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/incidents${qs}`,
  });
  if (!res.ok) {
    return [];
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) =>
    normalizeIncident(row as Record<string, unknown>),
  );
}

export async function acknowledgeMonitoringAlert(
  alertId: string,
): Promise<MonitoringAlert | null> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/monitoring/alerts/${encodeURIComponent(alertId)}/acknowledge`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Accusé de réception impossible."));
  }
  return normalizeAlert(res.data ?? {});
}

export async function resolveMonitoringAlert(
  alertId: string,
): Promise<MonitoringAlert | null> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/monitoring/alerts/${encodeURIComponent(alertId)}/resolve`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Résolution alerte impossible."));
  }
  return normalizeAlert(res.data ?? {});
}

export async function resolveMonitoringIncident(
  incidentId: string,
  resolutionNotes?: string,
): Promise<MonitoringIncident | null> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/monitoring/incidents/${encodeURIComponent(incidentId)}/resolve`,
    body: resolutionNotes ? { resolution_notes: resolutionNotes } : {},
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Résolution incident impossible."));
  }
  return normalizeIncident(res.data ?? {});
}

export async function runMonitoringCheck(): Promise<MonitoringCheckResult> {
  const res = await apiRequest<MonitoringCheckResult>({
    method: "POST",
    path: `${API_PREFIX}/monitoring/check`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Checks monitoring impossible."));
  }
  const data = res.data ?? ({} as MonitoringCheckResult);
  return {
    created: Array.isArray(data.created)
      ? data.created.map((row) =>
          normalizeAlert(row as unknown as Record<string, unknown>),
        )
      : [],
    skipped: Array.isArray(data.skipped) ? data.skipped : [],
    metrics:
      data.metrics && typeof data.metrics === "object" ? data.metrics : {},
    error: data.error,
  };
}

export function severityBadgeClass(severity: string): string {
  const s = severity.toLowerCase();
  if (s === "critical" || s === "high") {
    return "border-red-400/35 bg-red-500/15 text-red-200";
  }
  if (s === "warning" || s === "medium") {
    return "border-amber-400/35 bg-amber-500/15 text-amber-200";
  }
  return "border-teal-400/35 bg-teal-500/15 text-teal-200";
}

export function overallStatusBadgeClass(status: OverallStatus): string {
  if (status === "healthy") {
    return "border-teal-400/35 bg-teal-500/15 text-teal-200";
  }
  if (status === "degraded") {
    return "border-amber-400/35 bg-amber-500/15 text-amber-200";
  }
  return "border-red-400/35 bg-red-500/15 text-red-200 animate-pulse";
}

export function formatUsdEur(usd: number): string {
  const eur = usd * 0.92;
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(eur);
}
