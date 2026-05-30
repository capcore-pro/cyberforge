import { API_PREFIX } from "@shared/constants";
import type { ManagedProjectRecord, ManagedProjectRunRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";
import type { DeletionReport } from "@/lib/deletion-report";

export async function listVitrines() {
  return apiRequest<ManagedProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/vitrines`,
  });
}

export async function getVitrine(projectId: string) {
  return apiRequest<ManagedProjectRecord>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}`,
  });
}

export async function listVitrineRuns(projectId: string) {
  return apiRequest<ManagedProjectRunRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/runs`,
  });
}

export async function createVitrine(prompt: string, slug?: string) {
  return apiRequest<{ project: ManagedProjectRecord; run: ManagedProjectRunRecord }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines`,
    body: { prompt, slug: slug?.trim() || null },
    timeoutMs: 120_000,
  });
}

export async function updateVitrine(projectId: string, prompt: string) {
  return apiRequest<{ project: { id: string }; run: { status: string } }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/update`,
    body: { prompt },
    timeoutMs: 120_000,
  });
}

export async function deleteVitrine(projectId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/delete`,
    body: { hard_delete: false },
    timeoutMs: 120_000,
  });
}

export async function hardDeleteVitrine(projectId: string) {
  return apiRequest<DeletionReport>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/delete`,
    body: { hard_delete: true },
    timeoutMs: 120_000,
  });
}

export interface VitrineAuthInfo {
  enabled: boolean;
  client_email: string | null;
  password: string | null;
}

export async function fetchVitrineAuth(projectId: string) {
  return apiRequest<VitrineAuthInfo>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/auth`,
  });
}

export async function toggleVitrineAuth(projectId: string, enabled: boolean) {
  return apiRequest<VitrineAuthInfo>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/auth`,
    body: { enabled },
  });
}

export async function regenerateVitrinePassword(projectId: string) {
  return apiRequest<VitrineAuthInfo>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/auth`,
    body: { generate_password: true },
  });
}

