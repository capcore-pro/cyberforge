import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export type DemoDuration = "24h" | "48h" | "7d";

export interface DemoFileInput {
  path: string;
  content: string;
}

export interface CreateDemoPayload {
  duration: DemoDuration;
  title?: string;
  files: DemoFileInput[];
  stack?: string[];
  summary?: string | null;
  project_type?: string | null;
  code?: string | null;
  generation_id?: string | null;
}

export interface CreateDemoResponse {
  id: string;
  token: string;
  password: string;
  url: string;
  expires_at: string;
  duration_hours: number;
  title: string;
}

export interface DemoMetaResponse {
  title: string;
  expires_at: string;
  expired: boolean;
}

export interface DemoPayload {
  files: DemoFileInput[];
  stack: string[];
  summary: string | null;
  project_type: string | null;
  code: string | null;
}

export interface DemoUnlockResponse {
  title: string;
  expires_at: string;
  payload: DemoPayload;
}

export async function createClientDemo(body: CreateDemoPayload) {
  return apiRequest<CreateDemoResponse>({
    method: "POST",
    path: `${API_PREFIX}/demos`,
    body,
  });
}

export async function fetchDemoMeta(token: string) {
  return apiRequest<DemoMetaResponse>({
    method: "GET",
    path: `${API_PREFIX}/public/demos/${encodeURIComponent(token)}/meta`,
  });
}

export async function unlockClientDemo(token: string, password: string) {
  return apiRequest<DemoUnlockResponse>({
    method: "POST",
    path: `${API_PREFIX}/public/demos/${encodeURIComponent(token)}/unlock`,
    body: { password },
  });
}
