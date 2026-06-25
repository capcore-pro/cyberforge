import { API_PREFIX } from "@shared/constants";
import type { ProjectDetailResponse, ProjectRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

/** GET /api/projects — liste projets Supabase. */
export async function listSupabaseProjects() {
  return apiRequest<ProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/projects`,
  });
}

export async function fetchProjectDemoSeed(projectId: string) {
  return apiRequest<import("@shared/types").DemoSeedPayload>({
    method: "GET",
    path: `${API_PREFIX}/projects/${projectId}/demo-seed`,
  });
}

export async function deleteProject(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "DELETE",
    path: `${API_PREFIX}/projects/${projectId}`,
  });
}

export async function updateProject(
  projectId: string,
  body: {
    title?: string;
    prompt?: string;
    price_eur?: number;
    price_paid_at?: string;
    price_notes?: string;
  },
) {
  return apiRequest<ProjectRecord>({
    method: "PATCH",
    path: `${API_PREFIX}/projects/${projectId}`,
    body,
  });
}

export async function duplicateSupabaseProject(projectId: string) {
  return apiRequest<ProjectDetailResponse>({
    method: "POST",
    path: `${API_PREFIX}/projects/${projectId}/duplicate`,
  });
}

export async function updateManagedProjectTitle(projectId: string, title: string) {
  return apiRequest<{ id: string; title: string }>({
    method: "PATCH",
    path: `${API_PREFIX}/managed-projects/${projectId}`,
    body: { title },
  });
}
