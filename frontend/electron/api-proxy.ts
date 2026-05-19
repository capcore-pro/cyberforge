import type { ApiRequestPayload, ApiResponsePayload } from "@shared/ipc";
import { DEFAULT_API_BASE_URL } from "@shared/constants";

/** Résout l'URL de base du backend depuis l'environnement du processus main. */
export function resolveApiBaseUrl(): string {
  const fromEnv =
    process.env.VITE_API_BASE_URL?.trim() || process.env.BACKEND_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  return DEFAULT_API_BASE_URL;
}

/**
 * Proxifie une requête HTTP vers FastAPI depuis le processus principal.
 * Le renderer ne fournit qu'un chemin relatif (pas d'URL arbitraire).
 */
export async function proxyApiRequest(
  payload: ApiRequestPayload,
): Promise<ApiResponsePayload> {
  const { method = "GET", path, body, headers = {} } = payload;

  if (!path.startsWith("/") || path.includes("://")) {
    throw new Error("Chemin API invalide : doit être un chemin relatif.");
  }

  const url = `${resolveApiBaseUrl()}${path}`;
  const hasBody =
    body !== undefined && method !== "GET" && method !== "HEAD";

  const init: RequestInit = {
    method,
    headers: { ...headers },
  };

  if (hasBody) {
    init.headers = {
      "Content-Type": "application/json",
      ...init.headers,
    };
    init.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, init);
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
      data,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Erreur réseau vers le backend";
    return {
      ok: false,
      status: 0,
      statusText: message,
      data: null,
    };
  }
}
