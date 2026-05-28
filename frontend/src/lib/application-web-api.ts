import { API_PREFIX } from "@shared/constants";
import type { ManagedProjectRecord, ManagedProjectRunRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

export async function listApplicationWeb() {
  return apiRequest<ManagedProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/application-web`,
  });
}

export async function getApplicationWeb(projectId: string) {
  return apiRequest<ManagedProjectRecord>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/application-web/${projectId}`,
  });
}

export async function listApplicationWebRuns(projectId: string) {
  return apiRequest<ManagedProjectRunRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/application-web/${projectId}/runs`,
  });
}

export async function createApplicationWeb(prompt: string, slug?: string) {
  return apiRequest<{ project: ManagedProjectRecord; run: ManagedProjectRunRecord }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/application-web`,
    body: { prompt, slug: slug?.trim() || null },
    timeoutMs: 120_000,
  });
}

export async function updateApplicationWeb(projectId: string, prompt: string) {
  return apiRequest<{ project: { id: string }; run: { status: string } }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/application-web/${projectId}/update`,
    body: { prompt },
    timeoutMs: 120_000,
  });
}

export async function deleteApplicationWeb(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/application-web/${projectId}/delete`,
    body: { hard_delete: false },
    timeoutMs: 120_000,
  });
}

export async function hardDeleteApplicationWeb(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/application-web/${projectId}/delete`,
    body: { hard_delete: true },
    timeoutMs: 120_000,
  });
}

