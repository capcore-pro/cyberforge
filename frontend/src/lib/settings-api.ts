import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ProfileSettings {
  first_name: string;
  last_name: string;
  title: string;
  email: string;
  phone: string;
  siret: string;
  vat_number: string;
  address_street: string;
  address_postal_code: string;
  address_city: string;
  signature: string;
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
    method: "POST",
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

export async function fetchSystemLogs(limit = 5) {
  return apiRequest<{ lines: string[]; backend_port: number }>({
    method: "GET",
    path: `${API_PREFIX}/system/logs?limit=${limit}`,
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

export function systemLogsExportUrl(): string {
  const base =
    import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8002";
  const normalized = base.replace(/\/+$/, "").replace(/\/api$/i, "");
  return `${normalized}/api/system/logs/export`;
}
