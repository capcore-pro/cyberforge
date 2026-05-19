/**
 * Contrats IPC entre le renderer Electron et le processus principal.
 * Le main proxy les requêtes vers le backend FastAPI (pas de secrets ici).
 */

export const IPC_CHANNELS = {
  API_REQUEST: "api:request",
} as const;

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD";

/** Requête API envoyée par le renderer (chemin relatif uniquement). */
export interface ApiRequestPayload {
  method?: HttpMethod;
  /** Chemin relatif, ex. `/api/health` */
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
}

/** Réponse sérialisée renvoyée au renderer. */
export interface ApiResponsePayload<T = unknown> {
  ok: boolean;
  status: number;
  statusText: string;
  data: T;
}
