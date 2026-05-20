import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import {
  buildPublicDemoApiUrl,
  fetchBackendJson,
} from "@/lib/backend-url";

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
  preview_html: string;
  summary: string | null;
  project_type: string | null;
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

/** Métadonnées démo — appel direct vers http://127.0.0.1:8002/api/public/demos/{token}/meta */
export async function fetchDemoMeta(token: string) {
  const url = buildPublicDemoApiUrl(token, "meta");
  return fetchBackendJson<DemoMetaResponse>(url, { method: "GET" });
}

/** Déverrouillage démo — appel direct vers http://127.0.0.1:8002/api/public/demos/{token}/unlock */
export async function unlockClientDemo(token: string, password: string) {
  const url = buildPublicDemoApiUrl(token, "unlock");
  return fetchBackendJson<DemoUnlockResponse>(url, {
    method: "POST",
    body: { password },
  });
}
