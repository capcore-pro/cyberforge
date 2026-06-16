import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";
import { buildBackendApiUrl } from "@/lib/backend-url";

export type MobileAppMode = "client" | "product";
export type MobileAppSector =
  | "restaurant"
  | "artisan"
  | "commerce"
  | "service"
  | "vitrine";

export type MobileAppStatus =
  | "draft"
  | "generated"
  | "building"
  | "ready"
  | "failed";

export interface MobileScreenMeta {
  id: string;
  title: string;
  route: string;
}

export interface MobileAppRecord {
  id: string;
  name: string;
  description: string | null;
  mode: MobileAppMode;
  sector: MobileAppSector;
  primary_color: string;
  secondary_color: string;
  logo_url: string | null;
  app_slug: string;
  bundle_id: string | null;
  features: string[];
  screens: MobileScreenMeta[];
  status: MobileAppStatus;
  eas_build_id: string | null;
  apk_url: string | null;
  build_logs: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MobileAppUpsert {
  name: string;
  description: string;
  mode: MobileAppMode;
  sector: MobileAppSector;
  primary_color: string;
  secondary_color: string;
  logo_url?: string | null;
  app_slug: string;
  bundle_id: string;
  features: string[];
}

export interface MobileBuildRecord {
  id: string;
  app_id: string;
  build_number: number;
  eas_build_id: string | null;
  platform: string;
  status: string;
  apk_url: string | null;
  build_duration_ms: number | null;
  created_at: string | null;
}

export interface MobileBuildStatusResponse {
  app: MobileAppRecord;
  live: { status: string; apk_url: string | null; error?: string } | null;
  builds: MobileBuildRecord[];
}

export interface MobileGenerateDone {
  app_id: string;
  screens_count: number;
  features_count: number;
  files: string[];
}

export interface MobileGenerateHandlers {
  onAgentStart: (message: string) => void;
  onAgentDone: (message: string, extra?: Record<string, unknown>) => void;
  onDone: (payload: MobileGenerateDone) => void;
  onError: (message: string) => void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeScreen(row: unknown): MobileScreenMeta {
  const r = isRecord(row) ? row : {};
  return {
    id: String(r.id ?? ""),
    title: String(r.title ?? ""),
    route: String(r.route ?? ""),
  };
}

export function normalizeMobileApp(row: Record<string, unknown>): MobileAppRecord {
  const features = Array.isArray(row.features)
    ? row.features.map((x) => String(x))
    : [];
  const screens = Array.isArray(row.screens)
    ? row.screens.map(normalizeScreen)
    : [];
  return {
    id: String(row.id ?? ""),
    name: String(row.name ?? ""),
    description: row.description != null ? String(row.description) : null,
    mode: (row.mode as MobileAppMode) ?? "client",
    sector: (row.sector as MobileAppSector) ?? "vitrine",
    primary_color: String(row.primary_color ?? "#06b6d4"),
    secondary_color: String(row.secondary_color ?? "#8b5cf6"),
    logo_url: row.logo_url != null ? String(row.logo_url) : null,
    app_slug: String(row.app_slug ?? ""),
    bundle_id: row.bundle_id != null ? String(row.bundle_id) : null,
    features,
    screens,
    status: (row.status as MobileAppStatus) ?? "draft",
    eas_build_id: row.eas_build_id != null ? String(row.eas_build_id) : null,
    apk_url: row.apk_url != null ? String(row.apk_url) : null,
    build_logs: row.build_logs != null ? String(row.build_logs) : null,
    created_at: row.created_at != null ? String(row.created_at) : null,
    updated_at: row.updated_at != null ? String(row.updated_at) : null,
  };
}

export async function listMobileApps(): Promise<MobileAppRecord[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/mobile/apps`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les apps mobiles."));
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) => normalizeMobileApp(row as Record<string, unknown>));
}

export async function getMobileApp(id: string): Promise<MobileAppRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/mobile/apps/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "App introuvable."));
  }
  return normalizeMobileApp(res.data ?? {});
}

export async function createMobileApp(
  payload: MobileAppUpsert,
): Promise<MobileAppRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/mobile/apps`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Création impossible."));
  }
  return normalizeMobileApp(res.data ?? {});
}

export async function updateMobileApp(
  id: string,
  payload: Partial<MobileAppUpsert>,
): Promise<MobileAppRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "PUT",
    path: `${API_PREFIX}/mobile/apps/${encodeURIComponent(id)}`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Mise à jour impossible."));
  }
  return normalizeMobileApp(res.data ?? {});
}

export async function deleteMobileApp(id: string): Promise<void> {
  const res = await apiRequest<{ deleted?: boolean }>({
    method: "DELETE",
    path: `${API_PREFIX}/mobile/apps/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Suppression impossible."));
  }
}

function parseSseBlocks(text: string): Array<{ event?: string; data?: string }> {
  return text
    .split("\n\n")
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split("\n");
      const ev = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
      const data = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
      return { event: ev, data };
    });
}

export async function streamMobileGenerate(
  appId: string,
  handlers: MobileGenerateHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const path = `${API_PREFIX}/mobile/apps/${encodeURIComponent(appId)}/generate`;
  const url =
    import.meta.env.DEV && typeof window !== "undefined"
      ? path
      : buildBackendApiUrl(path);

  const response = await fetch(url, {
    method: "POST",
    headers: { Accept: "text/event-stream" },
    signal,
  });

  if (!response.ok || !response.body) {
    let detail = `Génération impossible (${response.status})`;
    try {
      const payload = (await response.json()) as unknown;
      detail = apiErrorMessage(
        { status: response.status, statusText: response.statusText, data: payload },
        detail,
      );
    } catch {
      // ignore
    }
    handlers.onError(detail);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      for (const parsed of parseSseBlocks(block)) {
        if (!parsed.event || !parsed.data) continue;
        try {
          const payload = JSON.parse(parsed.data) as unknown;
          const rec = isRecord(payload) ? payload : {};
          if (parsed.event === "agent_start") {
            handlers.onAgentStart(String(rec.message ?? ""));
          } else if (parsed.event === "agent_done") {
            handlers.onAgentDone(String(rec.message ?? ""), rec);
          } else if (parsed.event === "done") {
            handlers.onDone({
              app_id: String(rec.app_id ?? appId),
              screens_count: Number(rec.screens_count ?? 0),
              features_count: Number(rec.features_count ?? 0),
              files: Array.isArray(rec.files)
                ? rec.files.map((f) => String(f))
                : [],
            });
          } else if (parsed.event === "error") {
            handlers.onError(String(rec.message ?? "Erreur inconnue."));
          }
        } catch {
          // ignore malformed blocks
        }
      }
    }
  }
}

export async function triggerMobileBuild(
  appId: string,
): Promise<{ build_id: string; status: string; message: string }> {
  const res = await apiRequest<{
    build_id?: string;
    status?: string;
    message?: string;
  }>({
    method: "POST",
    path: `${API_PREFIX}/mobile/apps/${encodeURIComponent(appId)}/build`,
    timeoutMs: 120_000,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Build impossible."));
  }
  return {
    build_id: String(res.data?.build_id ?? ""),
    status: String(res.data?.status ?? ""),
    message: String(res.data?.message ?? ""),
  };
}

export async function fetchMobileBuildStatus(
  appId: string,
): Promise<MobileBuildStatusResponse> {
  const res = await apiRequest<{
    app?: Record<string, unknown>;
    live?: Record<string, unknown> | null;
    builds?: unknown[];
  }>({
    method: "GET",
    path: `${API_PREFIX}/mobile/apps/${encodeURIComponent(appId)}/status`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Statut build indisponible."));
  }
  const app = normalizeMobileApp(res.data?.app ?? {});
  const liveRaw = res.data?.live;
  const live =
    liveRaw && isRecord(liveRaw)
      ? {
          status: String(liveRaw.status ?? ""),
          apk_url:
            liveRaw.apk_url != null ? String(liveRaw.apk_url) : null,
          error: liveRaw.error != null ? String(liveRaw.error) : undefined,
        }
      : null;
  const builds = Array.isArray(res.data?.builds)
    ? res.data.builds.map((b) => {
        const row = isRecord(b) ? b : {};
        return {
          id: String(row.id ?? ""),
          app_id: String(row.app_id ?? ""),
          build_number: Number(row.build_number ?? 0),
          eas_build_id:
            row.eas_build_id != null ? String(row.eas_build_id) : null,
          platform: String(row.platform ?? "android"),
          status: String(row.status ?? ""),
          apk_url: row.apk_url != null ? String(row.apk_url) : null,
          build_duration_ms:
            row.build_duration_ms != null
              ? Number(row.build_duration_ms)
              : null,
          created_at: row.created_at != null ? String(row.created_at) : null,
        } satisfies MobileBuildRecord;
      })
    : [];
  return { app, live, builds };
}

export function getMobileApkDownloadUrl(appId: string): string {
  const path = `${API_PREFIX}/mobile/apps/${encodeURIComponent(appId)}/download`;
  return import.meta.env.DEV && typeof window !== "undefined"
    ? path
    : buildBackendApiUrl(path);
}

export const MOBILE_SECTORS: Array<{ id: MobileAppSector; label: string }> = [
  { id: "restaurant", label: "Restaurant" },
  { id: "artisan", label: "Artisan" },
  { id: "commerce", label: "Commerce" },
  { id: "service", label: "Service" },
  { id: "vitrine", label: "Vitrine" },
];

export const MOBILE_FEATURES: Array<{ id: string; label: string; icon: string }> = [
  { id: "auth", label: "Authentification", icon: "ti ti-lock" },
  { id: "push_notifications", label: "Push notifications", icon: "ti ti-bell" },
  { id: "geolocation", label: "Géolocalisation", icon: "ti ti-map-pin" },
  { id: "camera", label: "Caméra", icon: "ti ti-camera" },
  { id: "stripe_payment", label: "Paiement Stripe", icon: "ti ti-credit-card" },
  { id: "calendar", label: "Calendrier", icon: "ti ti-calendar" },
  { id: "chat", label: "Chat", icon: "ti ti-message" },
  { id: "offline_mode", label: "Mode offline", icon: "ti ti-cloud-off" },
];

export const SECTOR_SCREEN_HINTS: Record<MobileAppSector, string[]> = {
  restaurant: ["Menu", "Réservation", "Commande"],
  artisan: ["Devis", "Planning", "Clients", "Interventions"],
  commerce: ["Catalogue", "Panier", "Fidélité"],
  service: ["Prise de RDV", "Suivi", "Messagerie"],
  vitrine: ["Présentation", "Contact", "Galerie", "Avis"],
};
