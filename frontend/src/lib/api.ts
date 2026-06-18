import { API_PREFIX, DEFAULT_API_BASE_URL, normalizeBackendBaseUrl } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

async function request<T>(
  path: string,
  options?: { method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"; body?: unknown },
): Promise<T> {
  const normalizedPath = path.startsWith(API_PREFIX) ? path : `${API_PREFIX}${path}`;
  const response = await apiRequest<T>({
    method: options?.method ?? "GET",
    path: normalizedPath,
    body: options?.body,
  });

  if (!response.ok) {
    const detail =
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data
        ? String((response.data as { detail: unknown }).detail)
        : response.statusText;
    throw new Error(detail || "Erreur API");
  }

  return response.data as T;
}

/** Client HTTP minimal — GET/POST JSON via apiRequest (IPC ou fetch). */
export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body }),
};

/** URL de base pour téléchargements binaires (hors JSON apiRequest). */
export function resolveApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return "";
  }
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  return normalizeBackendBaseUrl(raw);
}
