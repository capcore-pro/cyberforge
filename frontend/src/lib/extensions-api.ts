import { API_PREFIX } from "@shared/constants";
import type { ManagedProjectRecord, ManagedProjectRunRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

export async function listExtensions() {
  return apiRequest<ManagedProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/extensions`,
  });
}

export async function createExtension(prompt: string, slug?: string) {
  return apiRequest<{ project: ManagedProjectRecord; run: ManagedProjectRunRecord }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/extensions`,
    body: { prompt, slug: slug?.trim() || null },
    timeoutMs: 120_000,
  });
}

export async function updateExtension(projectId: string, prompt: string) {
  return apiRequest<{ project: { id: string }; run: { status: string } }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/extensions/${projectId}/update`,
    body: { prompt },
    timeoutMs: 120_000,
  });
}

export async function deleteExtension(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/extensions/${projectId}/delete`,
    body: { hard_delete: false },
    timeoutMs: 120_000,
  });
}

export async function hardDeleteExtension(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/extensions/${projectId}/delete`,
    body: { hard_delete: true },
    timeoutMs: 120_000,
  });
}

