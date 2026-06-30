import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export type ElectronBuildModel = "one_shot" | "subscription";

export type ElectronBuildStatusValue =
  | "pending"
  | "building"
  | "success"
  | "failed";

export interface ElectronBuildRequest {
  project_id: string;
  client_name: string;
  client_email: string;
  app_name: string;
  app_description: string;
  model: ElectronBuildModel;
  price_one_shot?: number;
  price_monthly?: number;
  version?: string;
  assembled_html?: string;
  project_type?: string;
  database_schema?: Record<string, unknown>;
}

export interface ElectronBuildStatus {
  id: string;
  app_name: string;
  client_name: string;
  client_email: string;
  model: string;
  build_status: ElectronBuildStatusValue;
  download_url: string | null;
  license_key: string | null;
  github_repo: string | null;
  version: string;
  created_at: string;
  notified_at?: string | null;
}

export interface ElectronLicenseRow {
  id: string;
  build_id: string;
  client_email: string;
  license_key: string;
  model: ElectronBuildModel;
  is_active: boolean;
  created_at: string;
  electron_builds?: {
    app_name?: string;
    client_name?: string;
    model?: string;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeElectronBuild(row: Record<string, unknown>): ElectronBuildStatus {
  return {
    id: String(row.id ?? ""),
    app_name: String(row.app_name ?? ""),
    client_name: String(row.client_name ?? ""),
    client_email: String(row.client_email ?? ""),
    model: String(row.model ?? "one_shot"),
    build_status: (row.build_status as ElectronBuildStatusValue) ?? "pending",
    download_url: row.download_url != null ? String(row.download_url) : null,
    license_key: row.license_key != null ? String(row.license_key) : null,
    github_repo: row.github_repo != null ? String(row.github_repo) : null,
    version: String(row.version ?? "1.0.0"),
    created_at: String(row.created_at ?? ""),
    notified_at: row.notified_at != null ? String(row.notified_at) : null,
  };
}

export async function startBuild(
  data: ElectronBuildRequest,
): Promise<{ build_id: string; license_key: string; status?: string }> {
  const res = await apiRequest<{
    build_id?: string;
    license_key?: string;
    status?: string;
    success?: boolean;
  }>({
    method: "POST",
    path: `${API_PREFIX}/electron/build`,
    body: data,
    timeoutMs: 180_000,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Lancement de la compilation impossible."));
  }
  return {
    build_id: String(res.data?.build_id ?? ""),
    license_key: String(res.data?.license_key ?? ""),
    status: res.data?.status != null ? String(res.data.status) : undefined,
  };
}

export async function getBuildStatus(buildId: string): Promise<ElectronBuildStatus> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/electron/build/${encodeURIComponent(buildId)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Build introuvable."));
  }
  return normalizeElectronBuild(res.data ?? {});
}

export async function listBuilds(): Promise<{ builds: ElectronBuildStatus[] }> {
  const res = await apiRequest<{ builds?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/electron/builds`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les builds desktop."));
  }
  const builds = Array.isArray(res.data?.builds) ? res.data.builds : [];
  return {
    builds: builds.map((row) =>
      normalizeElectronBuild(isRecord(row) ? row : {}),
    ),
  };
}

export async function listLicenses(): Promise<{ licenses: ElectronLicenseRow[] }> {
  const res = await apiRequest<{ licenses?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/electron/licenses`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les licences."));
  }
  const licenses = Array.isArray(res.data?.licenses) ? res.data.licenses : [];
  return {
    licenses: licenses.map((row) => {
      const r = isRecord(row) ? row : {};
      const nested = isRecord(r.electron_builds) ? r.electron_builds : undefined;
      return {
        id: String(r.id ?? ""),
        build_id: String(r.build_id ?? ""),
        client_email: String(r.client_email ?? ""),
        license_key: String(r.license_key ?? ""),
        model: (r.model as ElectronBuildModel) ?? "one_shot",
        is_active: Boolean(r.is_active ?? true),
        created_at: String(r.created_at ?? ""),
        electron_builds: nested
          ? {
              app_name:
                nested.app_name != null ? String(nested.app_name) : undefined,
              client_name:
                nested.client_name != null
                  ? String(nested.client_name)
                  : undefined,
              model: nested.model != null ? String(nested.model) : undefined,
            }
          : undefined,
      };
    }),
  };
}

export async function notifyClientUpdate(
  buildId: string,
  notesMaj: string = "",
): Promise<{ success: boolean; message?: string; client_email?: string }> {
  const res = await apiRequest<{
    success?: boolean;
    message?: string;
    client_email?: string;
    error?: string;
  }>({
    method: "POST",
    path: `${API_PREFIX}/electron/notify`,
    body: { build_id: buildId, notes_maj: notesMaj },
    timeoutMs: 30_000,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Notification client impossible."));
  }
  if (!res.data?.success) {
    throw new Error(res.data?.error ?? res.data?.message ?? "Notification client impossible.");
  }
  return {
    success: true,
    message: res.data?.message != null ? String(res.data.message) : undefined,
    client_email:
      res.data?.client_email != null ? String(res.data.client_email) : undefined,
  };
}

export async function deactivateLicense(
  licenseKey: string,
): Promise<{ success: boolean }> {
  const res = await apiRequest<{ success?: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/electron/licenses/deactivate`,
    body: { license_key: licenseKey },
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Désactivation de licence impossible."));
  }
  return { success: Boolean(res.data?.success) };
}
