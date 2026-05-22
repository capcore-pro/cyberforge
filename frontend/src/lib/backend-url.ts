import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import type { ApiResponsePayload } from "@shared/ipc";

/** URL de base du backend FastAPI, sans slash final ni suffixe /api. */
export function getBackendBaseUrl(): string {
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  return normalizeBackendBaseUrl(raw);
}

/** Construit une URL absolue vers une route API backend. */
export function buildBackendApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getBackendBaseUrl()}${normalized}`;
}

/** URL publique démo : GET/POST /api/public/demos/{token}/… */
export function buildPublicDemoApiUrl(
  token: string,
  action: "meta" | "unlock",
): string {
  const safeToken = encodeURIComponent(token.trim());
  return buildBackendApiUrl(
    `${API_PREFIX}/public/demos/${safeToken}/${action}`,
  );
}

/** Requête fetch directe vers le backend (page /demo ouverte dans le navigateur). */
export async function fetchBackendJson<T>(
  url: string,
  init?: { method?: string; body?: unknown },
): Promise<ApiResponsePayload<T>> {
  const method = init?.method ?? "GET";
  const hasBody =
    init?.body !== undefined && method !== "GET" && method !== "HEAD";

  try {
    const response = await fetch(url, {
      method,
      headers: hasBody ? { "Content-Type": "application/json" } : undefined,
      body: hasBody ? JSON.stringify(init.body) : undefined,
    });

    const contentType = response.headers.get("content-type") ?? "";
    let data: unknown;
    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text.length > 0 ? text : null;
    }

    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      data: data as T,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erreur réseau vers le backend";
    return {
      ok: false,
      status: 0,
      statusText: message,
      data: null as T,
    };
  }
}
