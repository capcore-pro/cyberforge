import { API_PREFIX } from "@shared/constants";
import type { DemoSeedPayload } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

export async function fetchProjectDemoSeed(projectId: string) {
  return apiRequest<DemoSeedPayload>({
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
