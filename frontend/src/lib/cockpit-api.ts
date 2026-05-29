import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const COCKPIT = `${API_PREFIX}/cockpit`;

export type AlertLevel = "warning" | "critical" | "urgent";
export type TransactionType = "expense" | "topup";

export interface CockpitBalance {
  service_id: string;
  balance_eur: number;
  last_synced_at: string | null;
  service_name?: string;
}

export interface CockpitThresholds {
  service_id: string;
  warning_eur: number;
  critical_eur: number;
  urgent_eur: number;
}

export interface CockpitService {
  id: string;
  name: string;
  api_key_env: string;
  connector: string | null;
  currency: string;
  color: string | null;
  icon: string | null;
  enabled: boolean;
  created_at: string;
  balance: CockpitBalance | null;
  thresholds: CockpitThresholds;
  ping_ok: boolean;
}

export interface CockpitAlert {
  id: string;
  service_id: string;
  level: AlertLevel;
  message: string;
  read: boolean;
  created_at: string;
}

export interface CockpitTransaction {
  id: string;
  service_id: string;
  type: TransactionType;
  amount_eur: number;
  description: string | null;
  project_id: string | null;
  created_at: string;
}

export interface CockpitExpenses {
  today_eur: number;
  week_eur: number;
  month_eur: number;
  month_total_eur: number;
}

export interface CockpitDashboard {
  services: CockpitService[];
  balances: CockpitBalance[];
  unread_alerts: CockpitAlert[];
  unread_alerts_count: number;
  expenses: CockpitExpenses;
  spent_today_eur: number;
  spent_week_eur: number;
  spent_month_eur: number;
  month_total_eur: number;
}

export interface SyncAllResponse {
  synced: { service_id: string; balance_eur: number }[];
  errors: { service_id: string; error: string }[];
  count: number;
}

export const COCKPIT_CONNECTOR_OPTIONS: { value: string; label: string }[] = [
  { value: "anthropic", label: "Anthropic" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "replicate", label: "Replicate" },
  { value: "tavily", label: "Tavily" },
  { value: "v0", label: "v0" },
  { value: "railway", label: "Railway" },
  { value: "vercel", label: "Vercel" },
  { value: "cloudflare", label: "Cloudflare" },
  { value: "brevo", label: "Brevo" },
  { value: "github", label: "GitHub" },
  { value: "unsplash", label: "Unsplash" },
  { value: "manual", label: "Manuel" },
];

export function fetchCockpitAlerts(limit = 100) {
  return apiRequest<CockpitAlert[]>({
    method: "GET",
    path: `${COCKPIT}/alerts?limit=${limit}`,
    timeoutMs: 60_000,
  });
}

export function fetchCockpitDashboard() {
  return apiRequest<CockpitDashboard>({
    method: "GET",
    path: `${COCKPIT}/dashboard`,
    timeoutMs: 60_000,
  });
}

export function fetchCockpitServices() {
  return apiRequest<CockpitService[]>({
    method: "GET",
    path: `${COCKPIT}/services`,
    timeoutMs: 60_000,
  });
}

export function syncAllCockpitServices() {
  return apiRequest<SyncAllResponse>({
    method: "POST",
    path: `${COCKPIT}/sync-all`,
    timeoutMs: 120_000,
  });
}

export function topupCockpitService(
  serviceId: string,
  body: { amount_eur: number; description?: string },
) {
  return apiRequest<{
    transaction: CockpitTransaction;
    balance: CockpitBalance | null;
    alerts_created: CockpitAlert[];
  }>({
    method: "POST",
    path: `${COCKPIT}/services/${encodeURIComponent(serviceId)}/topup`,
    body,
  });
}

export function fetchCockpitTransactions(
  serviceId: string,
  params?: { limit?: number; type?: TransactionType },
) {
  const q = new URLSearchParams();
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.type) q.set("type", params.type);
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<CockpitTransaction[]>({
    method: "GET",
    path: `${COCKPIT}/services/${encodeURIComponent(serviceId)}/transactions${suffix}`,
  });
}

export function updateCockpitThresholds(
  serviceId: string,
  body: {
    warning_eur?: number;
    critical_eur?: number;
    urgent_eur?: number;
  },
) {
  return apiRequest<CockpitThresholds>({
    method: "PUT",
    path: `${COCKPIT}/services/${encodeURIComponent(serviceId)}/thresholds`,
    body,
  });
}

export function createCockpitService(body: {
  name: string;
  api_key_env: string;
  connector?: string | null;
  color?: string | null;
  icon?: string | null;
  currency?: string;
  enabled?: boolean;
}) {
  return apiRequest<CockpitService>({
    method: "POST",
    path: `${COCKPIT}/services`,
    body,
  });
}

export function updateCockpitService(
  serviceId: string,
  body: {
    name?: string;
    api_key_env?: string;
    connector?: string | null;
    color?: string | null;
    icon?: string | null;
    enabled?: boolean;
  },
) {
  return apiRequest<CockpitService>({
    method: "PUT",
    path: `${COCKPIT}/services/${encodeURIComponent(serviceId)}`,
    body,
  });
}

export function deleteCockpitService(serviceId: string) {
  return apiRequest<{ status: string; service_id: string }>({
    method: "DELETE",
    path: `${COCKPIT}/services/${encodeURIComponent(serviceId)}`,
  });
}

export function markCockpitAlertsRead(alertIds?: string[]) {
  return apiRequest<{ marked_read: number }>({
    method: "POST",
    path: `${COCKPIT}/alerts/read`,
    body: alertIds?.length ? { alert_ids: alertIds } : {},
  });
}
