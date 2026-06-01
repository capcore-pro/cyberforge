import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ProviderFlags {
  openai: boolean;
  anthropic: boolean;
  deepseek: boolean;
  gemini: boolean;
}

export interface InfraFlags {
  v0: boolean;
  replicate: boolean;
  tavily: boolean;
  railway: boolean;
  vercel: boolean;
  github: boolean;
  brevo: boolean;
  stripe: boolean;
  brave_search: boolean;
  exa: boolean;
  stitch: boolean;
}

export type VaultConfiguredFlags = ProviderFlags & InfraFlags;

export interface SecretsStatusResponse {
  has_vault: boolean;
  locked: boolean;
  configured: VaultConfiguredFlags;
  effective: ProviderFlags;
  vault_path: string;
}

export interface VaultKeysPayload {
  openai_api_key?: string | null;
  anthropic_api_key?: string | null;
  deepseek_api_key?: string | null;
  google_generative_ai_api_key?: string | null;
  v0_api_key?: string | null;
  replicate_api_key?: string | null;
  tavily_api_key?: string | null;
  railway_api_key?: string | null;
  vercel_token?: string | null;
  github_token?: string | null;
  brevo_api_key?: string | null;
  stripe_secret_key?: string | null;
  brave_search_api_key?: string | null;
  exa_api_key?: string | null;
  stitch_api_key?: string | null;
}

/** @deprecated Utiliser VaultKeysPayload */
export type LlmKeysPayload = VaultKeysPayload;

export async function fetchSecretsStatus() {
  return apiRequest<SecretsStatusResponse>({
    method: "GET",
    path: `${API_PREFIX}/secrets/status`,
  });
}

export async function unlockSecrets(password: string) {
  return apiRequest<{ ok: boolean; locked: boolean; effective: ProviderFlags }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/unlock`,
    body: { password },
  });
}

export async function lockSecrets() {
  return apiRequest<{ ok: boolean; locked: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/lock`,
  });
}

export async function resetSecrets() {
  return apiRequest<SecretsStatusResponse & { ok: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/reset`,
  });
}

export async function saveSecrets(password: string, keys: VaultKeysPayload) {
  return apiRequest<{
    ok: boolean;
    has_vault: boolean;
    locked: boolean;
    effective: ProviderFlags;
  }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/save`,
    body: { password, ...keys },
  });
}

export async function changeMasterPassword(
  oldPassword: string,
  newPassword: string,
) {
  return apiRequest<{
    ok: boolean;
    has_vault: boolean;
    locked: boolean;
    effective: ProviderFlags;
  }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/change-password`,
    body: { old_password: oldPassword, new_password: newPassword },
  });
}

export async function testSecretKey(provider: string, apiKey?: string) {
  return apiRequest<{ valid: boolean; message: string }>({
    method: "POST",
    path: `${API_PREFIX}/secrets/test`,
    body: { provider, api_key: apiKey?.trim() || null },
  });
}
