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

export interface ProjectCoverResponse {
  project_key: string;
  media_asset_id: string | null;
  asset: MediaAsset | null;
}

function resolveMediaFileUrl(relativePath: string): string {
  const normalized = relativePath.startsWith("/") ? relativePath : `/${relativePath}`;
  // Même logique que api-client : en dev, proxy Vite (/api → backend).
  if (import.meta.env.DEV) {
    return normalized;
  }
  return buildBackendApiUrl(normalized);
}

/** URL locale pour afficher ou copier un asset (stockage disque, pas R2). */
export function getAssetPublicUrl(asset: MediaAsset): string {
  if (asset.local_url?.startsWith("/")) {
    return resolveMediaFileUrl(asset.local_url);
  }
  return resolveMediaFileUrl(`${MEDIA}/files/${encodeURIComponent(asset.id)}`);
}

/** URL absolue pour copier/partager (clipboard, liens externes). */
export function getAssetAbsolutePublicUrl(asset: MediaAsset): string {
  const relative = getAssetPublicUrl(asset);
  if (/^https?:\/\//i.test(relative)) {
    return relative;
  }
  if (import.meta.env.DEV && typeof window !== "undefined") {
    return `${window.location.origin}${relative}`;
  }
  return relative;
}

export function getAssetThumbnailUrl(asset: MediaAsset): string {
  if (asset.type !== "image") {
    return "";
  }
  return getAssetPublicUrl(asset);
}

export function providerLabel(asset: MediaAsset): string {
  const tags = asset.tags.map((t) => t.toLowerCase());
  if (tags.includes("pexels")) return "Pexels";
  if (tags.includes("unsplash")) return "Unsplash";
  if (tags.includes("pexels_unsplash")) return "Pexels / Unsplash";
  if (tags.includes("replicate")) return "Replicate";
  if (asset.source === "upload") return "Upload";
  if (asset.source === "generated") return "Généré";
  return "Local";
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

  const url = resolveMediaFileUrl(`${MEDIA}/upload`);
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

export function generateMediaImage(body: {
  prompt: string;
  project_id?: string;
}) {
  return apiRequest<MediaAsset>({
    method: "POST",
    path: `${MEDIA}/generate`,
    body,
    timeoutMs: 180_000,
  });
}

export function searchMediaPhotos(query: string, count = 12) {
  const q = new URLSearchParams();
  q.set("q", query.trim());
  q.set("count", String(count));
  return apiRequest<MediaAsset[]>({
    method: "GET",
    path: `${MEDIA}/search?${q.toString()}`,
    timeoutMs: 120_000,
  });
}

export function upscaleMediaAsset(assetId: string, scale: 2 | 4) {
  return apiRequest<MediaAsset>({
    method: "POST",
    path: `${MEDIA}/upscale`,
    body: { asset_id: assetId, scale },
    timeoutMs: 300_000,
  });
}

export function isAssetUpscaled(asset: MediaAsset): boolean {
  return asset.tags.some((t) => t.toLowerCase() === "upscaled");
}

export function importMediaFromUrl(body: {
  url: string;
  filename?: string;
  tags?: string[];
  project_id?: string;
}) {
  return apiRequest<MediaAsset>({
    method: "POST",
    path: `${MEDIA}/import-url`,
    body,
    timeoutMs: 120_000,
  });
}

export function updateMediaAsset(
  id: string,
  body: { filename?: string; project_id?: string; tags?: string[] },
) {
  return apiRequest<MediaAsset>({
    method: "PATCH",
    path: `${MEDIA}/assets/${encodeURIComponent(id)}`,
    body,
  });
}

export function deleteMediaAsset(id: string) {
  return apiRequest<{ status: string; asset_id: string }>({
    method: "DELETE",
    path: `${MEDIA}/assets/${encodeURIComponent(id)}`,
  });
}

export function fetchProjectCover(projectKey: string) {
  return apiRequest<ProjectCoverResponse>({
    method: "GET",
    path: `${MEDIA}/project-covers/${encodeURIComponent(projectKey)}`,
  });
}

export function setProjectCover(projectKey: string, mediaAssetId: string) {
  return apiRequest<ProjectCoverResponse>({
    method: "PUT",
    path: `${MEDIA}/project-covers/${encodeURIComponent(projectKey)}`,
    body: { media_asset_id: mediaAssetId },
  });
}

export function clearProjectCover(projectKey: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "DELETE",
    path: `${MEDIA}/project-covers/${encodeURIComponent(projectKey)}`,
  });
}

export function formatBytes(bytes: number): string {
  const n = Number(bytes) || 0;
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / (1024 * 1024)).toFixed(2)} Mo`;
}
