import { API_PREFIX } from "@shared/constants";
import type { ApiResponsePayload } from "@shared/ipc";
import { apiRequest } from "@/lib/api-client";
import { buildBackendApiUrl } from "@/lib/backend-url";
import { apiErrorMessage } from "@/lib/api-errors";

export interface EditorHtmlPayload {
  generation_id: string;
  html: string;
  demo_url: string | null;
  project_title?: string | null;
  project_type?: string | null;
  is_desktop?: boolean;
  electron_files?: Record<string, string> | null;
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

export function redeployHTML(
  projectId: string,
  generationId: string,
  html: string,
  options?: { remove_watermark?: boolean },
) {
  return apiRequest<RedeployResult>({
    method: "POST",
    path: `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/redeploy`,
    body: {
      generation_id: generationId,
      html,
      remove_watermark: options?.remove_watermark ?? false,
    },
    timeoutMs: 180_000,
  });
}

function parseFilenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const match = /filename="?([^";]+)"?/i.exec(header);
  return match?.[1]?.trim() || fallback;
}

function slugifyFilename(title: string): string {
  return title
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 50) || "projet";
}

export async function downloadDesktopPackage(
  projectId: string,
  projectTitle: string,
): Promise<void> {
  const path = `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/download-desktop`;
  const url =
    import.meta.env.DEV && typeof window !== "undefined"
      ? path
      : buildBackendApiUrl(path);

  const response = await fetch(url);
  if (!response.ok) {
    let detail = "Téléchargement package desktop impossible";
    try {
      const payload = await response.json();
      detail = apiErrorMessage(
        { ok: false, status: response.status, statusText: response.statusText, data: payload },
        detail,
      );
    } catch {
      detail = `Téléchargement package desktop impossible (${response.status})`;
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const date = new Date().toISOString().slice(0, 10);
  const fallback = `${slugifyFilename(projectTitle)}-electron-${date}.zip`;
  const filename = parseFilenameFromDisposition(
    response.headers.get("Content-Disposition"),
    fallback,
  );

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function exportZip(projectId: string, projectTitle: string): Promise<void> {
  const path = `${API_PREFIX}/editor/${encodeURIComponent(projectId)}/export-zip`;
  const url =
    import.meta.env.DEV && typeof window !== "undefined"
      ? path
      : buildBackendApiUrl(path);

  const response = await fetch(url);
  if (!response.ok) {
    let detail = "Export ZIP impossible";
    try {
      const payload = await response.json();
      detail = apiErrorMessage(
        { ok: false, status: response.status, statusText: response.statusText, data: payload },
        detail,
      );
    } catch {
      detail = `Export ZIP impossible (${response.status})`;
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const date = new Date().toISOString().slice(0, 10);
  const fallback = `${slugifyFilename(projectTitle)}-${date}.zip`;
  const filename = parseFilenameFromDisposition(
    response.headers.get("Content-Disposition"),
    fallback,
  );

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
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
