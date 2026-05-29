import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ProfileSettings {
  email: string;
  siret: string;
  kbis_media_id: string | null;
}

export async function fetchProfileSettings() {
  return apiRequest<ProfileSettings>({
    method: "GET",
    path: `${API_PREFIX}/settings/profile`,
  });
}

export async function saveProfileSettings(body: Partial<ProfileSettings>) {
  return apiRequest<ProfileSettings>({
    method: "PATCH",
    path: `${API_PREFIX}/settings/profile`,
    body,
  });
}

export async function fetchSystemInfo() {
  return apiRequest<{ version: string; app_name: string }>({
    method: "GET",
    path: `${API_PREFIX}/system/info`,
  });
}

export async function clearSystemCache() {
  return apiRequest<{ ok: boolean; message: string }>({
    method: "POST",
    path: `${API_PREFIX}/system/clear-cache`,
  });
}

export async function restartBackend() {
  return apiRequest<{ ok: boolean; message: string }>({
    method: "POST",
    path: `${API_PREFIX}/system/restart-backend`,
  });
}
