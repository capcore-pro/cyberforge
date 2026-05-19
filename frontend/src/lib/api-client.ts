import { DEFAULT_API_BASE_URL, API_PREFIX } from "@shared/constants";
import type { ApiRequestPayload, ApiResponsePayload } from "@shared/ipc";

/** Indique si l'API IPC Electron est disponible dans le renderer. */
export function isElectronApiAvailable(): boolean {
  return typeof window.cyberforge?.api?.request === "function";
}

/**
 * Envoie une requête au backend via IPC (Electron) ou fetch direct (navigateur).
 */
export async function apiRequest<T = unknown>(
  payload: ApiRequestPayload,
): Promise<ApiResponsePayload<T>> {
  if (isElectronApiAvailable()) {
    return window.cyberforge!.api!.request(payload) as Promise<
      ApiResponsePayload<T>
    >;
  }

  const baseUrl =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const method = payload.method ?? "GET";
  const url = `${baseUrl.replace(/\/$/, "")}${payload.path}`;
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
