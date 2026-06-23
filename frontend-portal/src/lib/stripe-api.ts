// frontend-portal/src/lib/stripe-api.ts

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://cyberforge-backend-production.up.railway.app";

export interface PlanFeatures {
  name: string;
  description: string;
  features: string[];
  monthly_price_eur: number;
  yearly_price_eur: number;
  max_sites: number;
  can_edit_sections: boolean;
  can_edit_colors: boolean;
  can_edit_fonts: boolean;
  priority_support: boolean;
}

export interface PlansResponse {
  plans: Record<string, PlanFeatures>;
  trial_days: number;
  currency: string;
  live_mode: boolean;
}

export interface SubscriptionStatus {
  has_access: boolean;
  reason: string;
  plan: string;
  status: string;
  trial_days_left?: number;
  plan_details?: PlanFeatures;
  trial_ends_at?: string;
  subscription_ends_at?: string;
  billing_interval?: string;
}

export interface CheckoutResult {
  checkout_url: string;
  session_id: string;
  plan: string;
  plan_name: string;
  price_eur: number;
  interval: string;
}

export async function getPlans(): Promise<PlansResponse> {
  const res = await fetch(`${API_URL}/api/stripe-portal/plans`);
  if (!res.ok) throw new Error("Impossible de charger les plans");
  return res.json();
}

export async function getSubscriptionStatus(
  clientId: string,
): Promise<SubscriptionStatus> {
  const res = await fetch(`${API_URL}/api/stripe-portal/status/${clientId}`);
  if (!res.ok) throw new Error("Impossible de charger le statut");
  return res.json();
}

export async function createCheckout(
  clientId: string,
  plan: string,
  interval: "monthly" | "yearly",
): Promise<CheckoutResult> {
  const res = await fetch(`${API_URL}/api/stripe-portal/create-checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, plan, interval }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur création checkout");
  }
  return res.json();
}

export async function openCustomerPortal(clientId: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/stripe-portal/customer-portal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId }),
  });
  if (!res.ok) throw new Error("Impossible d'ouvrir le portail de facturation");
  const data = await res.json();
  return data.portal_url;
}

export async function waitForActiveSubscription(
  clientId: string,
  maxAttempts = 8,
): Promise<SubscriptionStatus> {
  for (let i = 0; i < maxAttempts; i += 1) {
    const status = await getSubscriptionStatus(clientId);
    if (status.status === "active" || status.has_access) {
      return status;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  return getSubscriptionStatus(clientId);
}
