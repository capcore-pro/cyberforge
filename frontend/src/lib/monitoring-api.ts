import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export interface MonitoringOverview {
  open_alerts_count: number;
  acknowledged_alerts_count: number;
  critical_alerts_count: number;
  warning_alerts_count: number;
  open_incidents_count: number;
  sources_count: number;
  sources_active: number;
}

export interface MonitoringSource {
  id: string;
  source_name: string;
  source_type: string;
  status: string;
  created_at: string;
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

export interface MonitoringScanResult {
  created: MonitoringAlert[];
  skipped: string[];
  metrics: Record<string, number>;
}

const EMPTY_OVERVIEW: MonitoringOverview = {
  open_alerts_count: 0,
  acknowledged_alerts_count: 0,
  critical_alerts_count: 0,
  warning_alerts_count: 0,
  open_incidents_count: 0,
  sources_count: 0,
  sources_active: 0,
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

function normalizeSource(row: Record<string, unknown>): MonitoringSource {
  return {
    id: String(row.id ?? ""),
    source_name: String(row.source_name ?? ""),
    source_type: String(row.source_type ?? ""),
    status: String(row.status ?? "active"),
    created_at: String(row.created_at ?? ""),
  };
}

export async function fetchMonitoringOverview(): Promise<MonitoringOverview> {
  const res = await apiRequest<MonitoringOverview>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/overview`,
  });
  if (!res.ok) {
    console.warn(
      apiErrorMessage(res, "Impossible de charger l'aperçu monitoring."),
    );
    return EMPTY_OVERVIEW;
  }
  return { ...EMPTY_OVERVIEW, ...(res.data ?? {}) };
}

export async function fetchMonitoringSources(): Promise<MonitoringSource[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/sources`,
  });
  if (!res.ok) {
    return [];
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) =>
    normalizeSource(row as Record<string, unknown>),
  );
}

export async function fetchMonitoringAlerts(
  status = "open",
): Promise<MonitoringAlert[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/monitoring/alerts?status=${encodeURIComponent(status)}&limit=50`,
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

export async function runMonitoringScan(): Promise<MonitoringScanResult> {
  const res = await apiRequest<MonitoringScanResult>({
    method: "POST",
    path: `${API_PREFIX}/monitoring/scan`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Scan monitoring impossible."));
  }
  const data = res.data ?? ({} as MonitoringScanResult);
  return {
    created: Array.isArray(data.created)
      ? data.created.map((row) =>
          normalizeAlert(row as unknown as Record<string, unknown>),
        )
      : [],
    skipped: Array.isArray(data.skipped) ? data.skipped : [],
    metrics:
      data.metrics && typeof data.metrics === "object" ? data.metrics : {},
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
