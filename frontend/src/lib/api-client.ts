import { DEFAULT_API_BASE_URL, API_PREFIX } from "@shared/constants";
import type { ApiRequestPayload, ApiResponsePayload } from "@shared/ipc";

/**
 * En dev, le renderer Electron charge localhost:5173 : on passe par le proxy Vite
 * (/api → :8002) au lieu de l'IPC, pour que les requêtes apparaissent comme en navigateur.
 */
function useViteDevProxy(): boolean {
  return import.meta.env.DEV;
}

/** Indique si l'API IPC Electron est disponible dans le renderer. */
export function isElectronApiAvailable(): boolean {
  if (useViteDevProxy()) {
    return false;
  }
  return typeof window.cyberforge?.api?.request === "function";
}

function resolveFetchBaseUrl(): string {
  if (useViteDevProxy()) {
    return "";
  }
  return import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
}

/**
 * Envoie une requête au backend via IPC (Electron packagé) ou fetch (navigateur / dev).
 */
export async function apiRequest<T = unknown>(
  payload: ApiRequestPayload,
): Promise<ApiResponsePayload<T>> {
  if (isElectronApiAvailable()) {
    try {
      return (await window.cyberforge!.api!.request(payload)) as ApiResponsePayload<T>;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Erreur IPC vers le backend";
      return {
        ok: false,
        status: 0,
        statusText: message,
        data: null as T,
      };
    }
  }

  const baseUrl = resolveFetchBaseUrl();
  const method = payload.method ?? "GET";
  const url = baseUrl
    ? `${baseUrl.replace(/\/$/, "")}${payload.path}`
    : payload.path;
  const hasBody =
    payload.body !== undefined && method !== "GET" && method !== "HEAD";

  try {
    const response = await fetch(url, {
      method,
      headers: hasBody
        ? { "Content-Type": "application/json", ...payload.headers }
        : payload.headers,
      body: hasBody ? JSON.stringify(payload.body) : undefined,
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

/** Vérifie la disponibilité du backend via la route santé. */
export async function checkBackendHealth(): Promise<boolean> {
  const response = await apiRequest({
    method: "GET",
    path: `${API_PREFIX}/health`,
  });
  return response.ok;
}
