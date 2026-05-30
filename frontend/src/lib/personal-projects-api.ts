import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const BASE = `${API_PREFIX}/personal-projects`;

export type PersonalUsage = "personal" | "one_shot" | "subscription";

export interface PersonalProject {
  id: string;
  title: string;
  usage_type: PersonalUsage;
  price_eur: number | null;
  commercial_description: string | null;
  project_key: string | null;
  supabase_project_id: string | null;
  managed_id: string | null;
  demo_id: string | null;
  app_type: string | null;
  sale_link: string | null;
  sales_count: number;
  revenue_eur: number;
  published_on_capcore: boolean;
  created_at: string;
  updated_at: string;
}

export interface DesktopTemplate {
  id: string;
  title: string;
  description: string;
  icon: string;
  preview_features: string[];
}

export const USAGE_LABELS: Record<PersonalUsage, string> = {
  personal: "Usage personnel",
  one_shot: "Vendre en one-shot",
  subscription: "Vendre en abonnement",
};

export async function fetchPersonalProjects() {
  return apiRequest<PersonalProject[]>({ method: "GET", path: BASE });
}

export async function fetchPersonalProject(id: string) {
  return apiRequest<PersonalProject>({
    method: "GET",
    path: `${BASE}/${encodeURIComponent(id)}`,
  });
}

export async function createPersonalProject(body: {
  title: string;
  usage_type?: PersonalUsage;
  price_eur?: number | null;
  commercial_description?: string | null;
  project_key?: string | null;
  supabase_project_id?: string | null;
  managed_id?: string | null;
  demo_id?: string | null;
  app_type?: string | null;
}) {
  return apiRequest<PersonalProject>({
    method: "POST",
    path: BASE,
    body,
  });
}

export async function updatePersonalProject(
  id: string,
  body: Partial<{
    title: string;
    usage_type: PersonalUsage;
    price_eur: number | null;
    commercial_description: string | null;
    project_key: string | null;
    supabase_project_id: string | null;
    managed_id: string | null;
    demo_id: string | null;
    sale_link: string | null;
    sales_count: number;
    revenue_eur: number;
  }>,
) {
  return apiRequest<PersonalProject>({
    method: "PATCH",
    path: `${BASE}/${encodeURIComponent(id)}`,
    body,
  });
}

export async function deletePersonalProject(id: string) {
  return apiRequest<void>({
    method: "DELETE",
    path: `${BASE}/${encodeURIComponent(id)}`,
  });
}

export async function convertPersonalToClient(id: string, clientId: string) {
  return apiRequest<{ converted: boolean; client_id: string; demo_id: string | null }>({
    method: "POST",
    path: `${BASE}/${encodeURIComponent(id)}/convert-to-client`,
    body: { client_id: clientId },
  });
}

export async function fetchDesktopTemplates() {
  return apiRequest<DesktopTemplate[]>({
    method: "GET",
    path: `${BASE}/templates`,
  });
}

export async function publishDesktopTemplate(
  appType: string,
  body: { price_eur: number; commercial_description: string },
) {
  return apiRequest<{
    project: PersonalProject;
    publish_url: string;
    message: string;
  }>({
    method: "POST",
    path: `${BASE}/templates/${encodeURIComponent(appType)}/publish`,
    body,
  });
}
