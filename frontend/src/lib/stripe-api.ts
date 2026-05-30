import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const STRIPE = `${API_PREFIX}/stripe`;

/** Identifiant interne du compte CapCore (mes revenus). */
export const STRIPE_CAPCORE_PROJECT_ID = "capcore";

export interface StripeScopeStatus {
  configured: boolean;
  project_id?: string;
  config: StripeConfig | null;
}

export interface ClientStripeApplyResult {
  applied: boolean;
  project_id: string;
  message: string;
}

export type StripeMode = "test" | "live";
export type TransactionStatus = "pending" | "paid" | "failed" | "refunded";
export type TransactionType = "one_shot" | "subscription";
export type SubscriptionStatus = "active" | "cancelled" | "past_due";
export type SubscriptionInterval = "day" | "week" | "month" | "year";

export interface StripeConfig {
  id: string;
  project_id: string;
  project_name: string;
  publishable_key: string;
  secret_key_encrypted?: string | null;
  webhook_secret_encrypted?: string | null;
  mode: StripeMode;
  currency: string;
  enabled: boolean;
  created_at: string;
}

export interface StripeTransaction {
  id: string;
  stripe_config_id: string;
  project_id: string;
  stripe_payment_intent_id: string;
  stripe_session_id?: string | null;
  type: TransactionType;
  amount_eur: number;
  status: TransactionStatus;
  customer_email?: string | null;
  description?: string | null;
  created_at: string;
}

export interface StripeSubscription {
  id: string;
  stripe_config_id: string;
  project_id: string;
  stripe_subscription_id: string;
  customer_email: string;
  plan_name: string;
  amount_eur: number;
  status: SubscriptionStatus;
  current_period_end?: string | null;
  created_at: string;
}

export interface StripeDashboard {
  project_id: string | null;
  total_collected_eur: number;
  revenue_this_month_eur: number;
  active_subscriptions_count: number;
  active_subscriptions_mrr_eur: number;
  recent_transactions: StripeTransaction[];
  active_subscriptions: StripeSubscription[];
}

export interface StripeConfigCreatePayload {
  project_id: string;
  project_name: string;
  publishable_key: string;
  secret_key: string;
  webhook_secret?: string | null;
  mode?: StripeMode;
  currency?: string;
  enabled?: boolean;
}

export interface StripeConfigUpdatePayload {
  project_id?: string;
  project_name?: string;
  publishable_key?: string;
  secret_key?: string;
  webhook_secret?: string | null;
  mode?: StripeMode;
  currency?: string;
  enabled?: boolean;
}

export interface SubscriptionLinkPayload {
  project_id: string;
  plan_name: string;
  amount_eur: number;
  interval?: SubscriptionInterval;
  customer_email?: string | null;
}

export async function fetchCapcoreStripe() {
  return apiRequest<StripeScopeStatus>({
    method: "GET",
    path: `${STRIPE}/capcore`,
  });
}

export async function saveCapcoreStripe(body: {
  secret_key: string;
  publishable_key?: string | null;
  webhook_secret?: string | null;
  mode?: StripeMode;
}) {
  return apiRequest<StripeScopeStatus>({
    method: "PUT",
    path: `${STRIPE}/capcore`,
    body,
  });
}

export async function fetchClientStripe(projectId: string) {
  return apiRequest<StripeScopeStatus>({
    method: "GET",
    path: `${STRIPE}/projects/${encodeURIComponent(projectId)}`,
  });
}

export async function saveClientStripe(
  projectId: string,
  body: {
    secret_key: string;
    webhook_secret?: string | null;
    publishable_key?: string | null;
    mode?: StripeMode;
    project_name?: string;
  },
) {
  return apiRequest<StripeScopeStatus>({
    method: "PUT",
    path: `${STRIPE}/projects/${encodeURIComponent(projectId)}`,
    body,
  });
}

export async function applyClientStripe(projectId: string) {
  return apiRequest<ClientStripeApplyResult>({
    method: "POST",
    path: `${STRIPE}/projects/${encodeURIComponent(projectId)}/apply`,
  });
}

export async function fetchStripeDashboard(projectId?: string) {
  const path = projectId
    ? `${STRIPE}/dashboard/${encodeURIComponent(projectId)}`
    : `${STRIPE}/dashboard`;
  return apiRequest<StripeDashboard>({ method: "GET", path });
}

export async function fetchStripeConfigs() {
  return apiRequest<StripeConfig[]>({ method: "GET", path: `${STRIPE}/configs` });
}

export async function createStripeConfig(body: StripeConfigCreatePayload) {
  return apiRequest<StripeConfig>({
    method: "POST",
    path: `${STRIPE}/configs`,
    body,
  });
}

export async function updateStripeConfig(
  configId: string,
  body: StripeConfigUpdatePayload,
) {
  return apiRequest<StripeConfig>({
    method: "PUT",
    path: `${STRIPE}/configs/${encodeURIComponent(configId)}`,
    body,
  });
}

export async function deleteStripeConfig(configId: string) {
  return apiRequest<{ ok: boolean }>({
    method: "DELETE",
    path: `${STRIPE}/configs/${encodeURIComponent(configId)}`,
  });
}

export async function fetchStripeTransactions(params?: {
  project_id?: string;
  status?: TransactionStatus;
  type?: TransactionType;
  limit?: number;
}) {
  const q = new URLSearchParams();
  if (params?.project_id) q.set("project_id", params.project_id);
  if (params?.status) q.set("status", params.status);
  if (params?.type) q.set("type", params.type);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiRequest<StripeTransaction[]>({
    method: "GET",
    path: `${STRIPE}/transactions${qs ? `?${qs}` : ""}`,
  });
}

export async function fetchStripeSubscriptions(params?: {
  project_id?: string;
  status?: SubscriptionStatus;
  limit?: number;
}) {
  const q = new URLSearchParams();
  if (params?.project_id) q.set("project_id", params.project_id);
  if (params?.status) q.set("status", params.status);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return apiRequest<StripeSubscription[]>({
    method: "GET",
    path: `${STRIPE}/subscriptions${qs ? `?${qs}` : ""}`,
  });
}

export async function createSubscriptionLink(body: SubscriptionLinkPayload) {
  return apiRequest<{ url: string }>({
    method: "POST",
    path: `${STRIPE}/subscription-link`,
    body,
  });
}

export async function cancelStripeSubscription(subscriptionId: string) {
  return apiRequest<StripeSubscription>({
    method: "PUT",
    path: `${STRIPE}/subscriptions/${encodeURIComponent(subscriptionId)}/cancel`,
  });
}
