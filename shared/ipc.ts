/**
 * Contrats IPC entre le renderer Electron et le processus principal.
 * Le main proxy les requêtes vers le backend FastAPI (pas de secrets ici).
 */

export const IPC_CHANNELS = {
  API_REQUEST: "api:request",
  PREVIEW_OPEN: "preview:open",
  OPEN_EXTERNAL: "shell:open-external",
  NOTIFY: "shell:notify",
  UPDATE_READY: "app:update-ready",
  RESTART_AND_UPDATE: "app:restart-and-update",
} as const;

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD";

/** Requête API envoyée par le renderer (chemin relatif uniquement). */
export interface ApiRequestPayload {
  method?: HttpMethod;
  /** Chemin relatif, ex. `/api/health` */
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Délai max (ms) — évite les requêtes pendantes si le backend redémarre */
  timeoutMs?: number;
}

/** Réponse sérialisée renvoyée au renderer. */
export interface ApiResponsePayload<T = unknown> {
  ok: boolean;
  status: number;
  statusText: string;
  data: T;
}

/** Ouverture d'une fenêtre de prévisualisation (processus principal Electron). */
export interface PreviewOpenPayload {
  html: string;
  title?: string;
}
