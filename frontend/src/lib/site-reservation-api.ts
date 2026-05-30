import type { ManagedProjectRecord } from "@shared/types";
import type { DeletionReport } from "@/lib/deletion-report";

export interface ApiResp<T> {
  ok: boolean;
  status: number;
  data?: T;
  error?: unknown;
}

async function api<T>(path: string, init?: RequestInit): Promise<ApiResp<T>> {
  try {
    const r = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    const text = await r.text();
    let data: unknown = undefined;
    try {
      data = text ? JSON.parse(text) : undefined;
    } catch {
      data = text;
    }
    if (!r.ok) return { ok: false, status: r.status, error: data };
    return { ok: true, status: r.status, data: data as T };
  } catch (error) {
    return { ok: false, status: 0, error };
  }
}

export async function listReservationSites() {
  return api<ManagedProjectRecord[]>("/api/managed-projects/site-reservation");
}

export async function createReservationSite(prompt: string, slug?: string) {
  return api<{ project: ManagedProjectRecord } | any>("/api/managed-projects/site-reservation", {
    method: "POST",
    body: JSON.stringify({ prompt, slug }),
  });
}

export async function updateReservationSite(projectId: string, prompt: string) {
  return api<any>(`/api/managed-projects/site-reservation/${projectId}/update`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function deleteReservationSite(projectId: string) {
  return api<any>(`/api/managed-projects/site-reservation/${projectId}/delete`, {
    method: "POST",
    body: JSON.stringify({ hard_delete: false }),
  });
}

export async function hardDeleteReservationSite(projectId: string) {
  return api<DeletionReport>(`/api/managed-projects/site-reservation/${projectId}/delete`, {
    method: "POST",
    body: JSON.stringify({ hard_delete: true }),
  });
}

