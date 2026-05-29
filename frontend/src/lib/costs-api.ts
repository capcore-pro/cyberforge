import { API_PREFIX } from "@shared/constants";
import type {
  ProjectCostsResponse,
  ResetProjectCostsResponse,
} from "@shared/types";
import { apiRequest } from "@/lib/api-client";

export async function fetchProjectCosts(projectId: string) {
  const id = encodeURIComponent(projectId.trim());
  return apiRequest<ProjectCostsResponse>({
    method: "GET",
    path: `${API_PREFIX}/projects/${id}/costs`,
  });
}

export async function resetProjectCosts(projectId: string) {
  const id = encodeURIComponent(projectId.trim());
  return apiRequest<ResetProjectCostsResponse>({
    method: "DELETE",
    path: `${API_PREFIX}/projects/${id}/costs`,
  });
}
