/**
 * Constantes partagées entre le frontend et la documentation.
 * Les secrets et clés API ne doivent jamais figurer ici.
 */

export const APP_NAME = "CyberForge" as const;

declare const __APP_VERSION__: string;
export const APP_VERSION = __APP_VERSION__;

/** Préfixe des routes API REST */
export const API_PREFIX = "/api" as const;

/** URL de base du backend FastAPI (défaut local) */
export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8002" as const;

/** Racine backend sans slash final ni suffixe `/api` (évite /api/api/…). */
export function normalizeBackendBaseUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}
