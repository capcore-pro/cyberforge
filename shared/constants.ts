/**
 * Constantes partagées entre le frontend et la documentation.
 * Les secrets et clés API ne doivent jamais figurer ici.
 */

export const APP_NAME = "CyberForge" as const;

/** Renderer : injecté par Vite (`define`). Main/preload : fallback via `app.getVersion()`. */
declare const __APP_VERSION__: string | undefined;
export const APP_VERSION =
  typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.0.0";

/** Préfixe des routes API REST */
export const API_PREFIX = "/api" as const;

/** URL de base du backend FastAPI (défaut local) */
export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8002" as const;

/** Racine backend sans slash final ni suffixe `/api` (évite /api/api/…). */
export function normalizeBackendBaseUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}
