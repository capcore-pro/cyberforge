import { API_PREFIX } from "@shared/constants";
import type { ApiResponsePayload } from "@shared/ipc";
import { apiRequest } from "@/lib/api-client";
import { buildBackendApiUrl } from "@/lib/backend-url";

export interface EditorHtmlPayload {
  generation_id: string;
  html: string;
  demo_url: string | null;
  project_title?: string | null;
}

export interface SaveHtmlResult {
  saved: boolean;
}

export interface RedeployResult {
  url: string;
  saved: boolean;
}

export interface UploadImageResult {
  image_url: string;
}

export function fetchProjectHTML(projectId: string) {
  return apiRequest<EditorHtmlPayload>({
    method: "GET",
    path: `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/html`,
  });
}

export function saveHTML(projectId: string, generationId: string, html: string) {
  return apiRequest<SaveHtmlResult>({
    method: "PATCH",
    path: `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/html`,
    body: { generation_id: generationId, html },
  });
}

export function redeployHTML(projectId: string, generationId: string, html: string) {
  return apiRequest<RedeployResult>({
    method: "POST",
    path: `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/redeploy`,
    body: { generation_id: generationId, html },
    timeoutMs: 180_000,
  });
}

export async function uploadImage(
  projectId: string,
  file: File,
): Promise<ApiResponsePayload<UploadImageResult>> {
  const form = new FormData();
  form.append("file", file);

  const path = `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/upload-image`;
  const url =
    import.meta.env.DEV && typeof window !== "undefined"
      ? path
      : buildBackendApiUrl(path);

  try {
    const response = await fetch(url, { method: "POST", body: form });
    const data = (await response.json()) as UploadImageResult;
    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      data,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Upload impossible";
    return { ok: false, status: 0, statusText: message, data: null as unknown as UploadImageResult };
  }
}
