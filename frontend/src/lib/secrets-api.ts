import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ProviderFlags {
  openai: boolean;
  anthropic: boolean;
  deepseek: boolean;
  gemini: boolean;
}

export interface SecretsStatusResponse {
  has_vault: boolean;
  locked: boolean;
  configured: ProviderFlags;
  effective: ProviderFlags;
  vault_path: string;
}

export interface LlmKeysPayload {
  openai_api_key?: string | null;
  anthropic_api_key?: string | null;
  deepseek_api_key?: string | null;
  google_generative_ai_api_key?: string | null;
}

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

export async function saveSecrets(password: string, keys: LlmKeysPayload) {
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
