import { API_PREFIX } from "@shared/constants";
import type { ApiResponsePayload } from "@shared/ipc";
import { apiRequest } from "@/lib/api-client";
import { buildBackendApiUrl } from "@/lib/backend-url";

const MEDIA = `${API_PREFIX}/media`;

export type MediaType = "image" | "zip" | "pdf";
export type MediaSource = "upload" | "generated";

export interface MediaAsset {
  id: string;
  filename: string;
  type: MediaType;
  mime_type: string;
  size_bytes: number;
  local_path: string;
  local_url: string | null;
  r2_url: string | null;
  r2_key: string | null;
  project_id: string | null;
  source: MediaSource;
  tags: string[];
  created_at: string;
}

export interface MediaListParams {
  type?: MediaType;
  source?: MediaSource;
  project_id?: string;
  search?: string;
  limit?: number;
}

function resolveMediaUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (import.meta.env.DEV && typeof window !== "undefined") {
    const useProxy =
      !import.meta.env.VITE_API_BASE_URL?.trim() ||
      import.meta.env.VITE_API_BASE_URL.includes("127.0.0.1:5173");
    if (useProxy) {
      return normalized;
    }
  }
  return buildBackendApiUrl(normalized);
}

/** URL pour afficher ou télécharger le fichier (API locale ou R2 public). */
export function getAssetPublicUrl(asset: MediaAsset): string {
  if (asset.r2_url?.trim()) {
    return asset.r2_url.trim();
  }
  if (asset.local_url?.startsWith("/")) {
    return resolveMediaUrl(asset.local_url);
  }
  return resolveMediaUrl(`${MEDIA}/files/${encodeURIComponent(asset.id)}`);
}

export function getAssetThumbnailUrl(asset: MediaAsset): string {
  if (asset.type !== "image") {
    return "";
  }
  return resolveMediaUrl(`${MEDIA}/files/${encodeURIComponent(asset.id)}`);
}

export function fetchMediaAssets(params: MediaListParams = {}) {
  const q = new URLSearchParams();
  if (params.type) q.set("type", params.type);
  if (params.source) q.set("source", params.source);
  if (params.project_id) q.set("project_id", params.project_id);
  if (params.search?.trim()) q.set("search", params.search.trim());
  if (params.limit) q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<MediaAsset[]>({
    method: "GET",
    path: `${MEDIA}/assets${suffix}`,
    timeoutMs: 60_000,
  });
}

export function fetchMediaAsset(id: string) {
  return apiRequest<MediaAsset>({
    method: "GET",
    path: `${MEDIA}/assets/${encodeURIComponent(id)}`,
  });
}

export async function uploadMediaAsset(
  file: File,
  opts?: { project_id?: string; tags?: string },
): Promise<ApiResponsePayload<MediaAsset>> {
  const form = new FormData();
  form.append("file", file);
  if (opts?.project_id?.trim()) {
    form.append("project_id", opts.project_id.trim());
  }
  if (opts?.tags?.trim()) {
    form.append("tags", opts.tags.trim());
  }

  const url = resolveMediaUrl(`${MEDIA}/upload`);
  try {
    const response = await fetch(url, {
      method: "POST",
      body: form,
    });
    const contentType = response.headers.get("content-type") ?? "";
    let data: unknown;
    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }
    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      data: data as MediaAsset,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erreur réseau vers le backend";
    return {
      ok: false,
      status: 0,
      statusText: message,
      data: null as MediaAsset,
    };
  }
}

export function deleteMediaAsset(id: string) {
  return apiRequest<{ status: string; asset_id: string }>({
    method: "DELETE",
    path: `${MEDIA}/assets/${encodeURIComponent(id)}`,
  });
}

export function syncMediaAssetR2(id: string, syncNow = true) {
  const q = syncNow ? "?sync_now=true" : "";
  return apiRequest<MediaAsset>({
    method: "POST",
    path: `${MEDIA}/assets/${encodeURIComponent(id)}/sync-r2${q}`,
    timeoutMs: 120_000,
  });
}

export function syncAllMediaR2() {
  return apiRequest<{ status: string; message?: string }>({
    method: "POST",
    path: `${MEDIA}/sync-r2`,
  });
}

export function formatBytes(bytes: number): string {
  const n = Number(bytes) || 0;
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / (1024 * 1024)).toFixed(2)} Mo`;
}
