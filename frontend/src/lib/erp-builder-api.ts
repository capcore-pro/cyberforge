import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";
import { buildBackendApiUrl } from "@/lib/backend-url";

export type ErpType = "odoo" | "erpnext" | "custom";
export type CompanySize = "solo" | "small" | "medium" | "large";
export type Budget = "low" | "medium" | "high";
export type ErpStatus =
  | "draft"
  | "configuring"
  | "installing"
  | "running"
  | "error"
  | "stopped";

export type ErpModuleId =
  | "facturation"
  | "stocks"
  | "rh"
  | "crm"
  | "projets"
  | "comptabilite";

export interface ErpProjectRecord {
  id: string;
  name: string;
  client_name: string | null;
  erp_type: ErpType | null;
  company_size: CompanySize;
  budget: Budget;
  modules: ErpModuleId[];
  primary_color: string;
  logo_url: string | null;
  domain: string | null;
  admin_email: string | null;
  admin_password: string | null;
  container_name: string | null;
  port: number | null;
  status: ErpStatus;
  url: string | null;
  install_logs: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ErpProjectUpsert {
  name: string;
  client_name: string;
  company_size: CompanySize;
  budget: Budget;
  modules: ErpModuleId[];
  erp_type?: ErpType | null;
  primary_color: string;
  logo_url?: string | null;
  domain?: string | null;
  admin_email: string;
  admin_password: string;
  port?: number | null;
}

export interface ErpRecommendation {
  erp_type: ErpType;
  label: string;
  description: string;
  reason: string;
  modules: ErpModuleId[];
  module_labels: string[];
  estimated_price_eur: number;
  startup_guide: string;
  alternatives: Array<{ erp_type: string; label: string; description: string }>;
}

export interface ErpDockerStatus {
  status: string;
  running: boolean;
  url: string | null;
  stats: {
    cpu_percent: string | null;
    mem_usage: string | null;
    mem_limit: string | null;
  };
  logs_tail: string[];
  error?: string;
}

export interface ErpInstallDone {
  url: string;
  admin_email: string;
  admin_password: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeErpProject(row: Record<string, unknown>): ErpProjectRecord {
  const modules = Array.isArray(row.modules)
    ? (row.modules.map((m) => String(m)) as ErpModuleId[])
    : [];
  return {
    id: String(row.id ?? ""),
    name: String(row.name ?? ""),
    client_name: row.client_name != null ? String(row.client_name) : null,
    erp_type: row.erp_type != null ? (String(row.erp_type) as ErpType) : null,
    company_size: (row.company_size as CompanySize) ?? "small",
    budget: (row.budget as Budget) ?? "medium",
    modules,
    primary_color: String(row.primary_color ?? "#0f1117"),
    logo_url: row.logo_url != null ? String(row.logo_url) : null,
    domain: row.domain != null ? String(row.domain) : null,
    admin_email: row.admin_email != null ? String(row.admin_email) : null,
    admin_password: row.admin_password != null ? String(row.admin_password) : null,
    container_name: row.container_name != null ? String(row.container_name) : null,
    port: row.port != null ? Number(row.port) : null,
    status: (row.status as ErpStatus) ?? "draft",
    url: row.url != null ? String(row.url) : null,
    install_logs: row.install_logs != null ? String(row.install_logs) : null,
    created_at: row.created_at != null ? String(row.created_at) : null,
    updated_at: row.updated_at != null ? String(row.updated_at) : null,
  };
}

export async function listErpProjects(): Promise<ErpProjectRecord[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/erp/projects`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les projets ERP."));
  }
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) => normalizeErpProject(row as Record<string, unknown>));
}

export async function createErpProject(payload: ErpProjectUpsert): Promise<ErpProjectRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/erp/projects`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Création impossible."));
  }
  return normalizeErpProject(res.data ?? {});
}

export async function updateErpProject(
  id: string,
  payload: Partial<ErpProjectUpsert> & { erp_type?: ErpType; status?: ErpStatus },
): Promise<ErpProjectRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "PUT",
    path: `${API_PREFIX}/erp/projects/${encodeURIComponent(id)}`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Mise à jour impossible."));
  }
  return normalizeErpProject(res.data ?? {});
}

export async function deleteErpProject(id: string): Promise<void> {
  const res = await apiRequest<{ deleted?: boolean }>({
    method: "DELETE",
    path: `${API_PREFIX}/erp/projects/${encodeURIComponent(id)}`,
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

async function streamSse(
  path: string,
  handlers: {
    onEvent: (event: string, data: Record<string, unknown>) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
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
    handlers.onError(`Requête impossible (${response.status})`);
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
          if (isRecord(payload)) {
            handlers.onEvent(parsed.event, payload);
          }
        } catch {
          // ignore
        }
      }
    }
  }
}

export async function streamErpRecommend(
  projectId: string,
  handlers: {
    onStart: (message: string) => void;
    onDone: (rec: ErpRecommendation) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  await streamSse(
    `${API_PREFIX}/erp/projects/${encodeURIComponent(projectId)}/recommend`,
    {
      onEvent: (event, data) => {
        if (event === "agent_start") {
          handlers.onStart(String(data.message ?? ""));
        } else if (event === "done") {
          handlers.onDone(data as unknown as ErpRecommendation);
        } else if (event === "error") {
          handlers.onError(String(data.message ?? "Erreur"));
        }
      },
      onError: handlers.onError,
    },
    signal,
  );
}

export async function streamErpInstall(
  projectId: string,
  handlers: {
    onStep: (message: string) => void;
    onLog: (message: string) => void;
    onDone: (payload: ErpInstallDone) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  await streamSse(
    `${API_PREFIX}/erp/projects/${encodeURIComponent(projectId)}/install`,
    {
      onEvent: (event, data) => {
        if (event === "step" || event === "agent_start") {
          handlers.onStep(String(data.message ?? ""));
        } else if (event === "log") {
          handlers.onLog(String(data.message ?? ""));
        } else if (event === "done") {
          handlers.onDone({
            url: String(data.url ?? ""),
            admin_email: String(data.admin_email ?? ""),
            admin_password: String(data.admin_password ?? ""),
          });
        } else if (event === "error") {
          handlers.onError(String(data.message ?? "Erreur installation"));
        }
      },
      onError: handlers.onError,
    },
    signal,
  );
}

export async function fetchErpStatus(projectId: string): Promise<{
  project: ErpProjectRecord;
  docker: ErpDockerStatus;
}> {
  const res = await apiRequest<{
    project?: Record<string, unknown>;
    docker?: Record<string, unknown>;
  }>({
    method: "GET",
    path: `${API_PREFIX}/erp/projects/${encodeURIComponent(projectId)}/status`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Statut indisponible."));
  }
  const dockerRaw = res.data?.docker ?? {};
  const dockerRec = isRecord(dockerRaw) ? dockerRaw : {};
  const statsRaw = dockerRec.stats;
  const statsRec = isRecord(statsRaw) ? statsRaw : {};
  return {
    project: normalizeErpProject(res.data?.project ?? {}),
    docker: {
      status: String(dockerRec.status ?? ""),
      running: Boolean(dockerRec.running),
      url: dockerRec.url != null ? String(dockerRec.url) : null,
      stats: {
        cpu_percent: statsRec.cpu_percent != null ? String(statsRec.cpu_percent) : null,
        mem_usage: statsRec.mem_usage != null ? String(statsRec.mem_usage) : null,
        mem_limit: statsRec.mem_limit != null ? String(statsRec.mem_limit) : null,
      },
      logs_tail: Array.isArray(dockerRec.logs_tail)
        ? dockerRec.logs_tail.map((l) => String(l))
        : [],
      error: dockerRec.error != null ? String(dockerRec.error) : undefined,
    },
  };
}

export async function stopErpProject(id: string): Promise<void> {
  const res = await apiRequest<{ stopped?: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/erp/projects/${encodeURIComponent(id)}/stop`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Arrêt impossible."));
  }
}

export async function restartErpProject(id: string): Promise<void> {
  const res = await apiRequest<{ restarted?: boolean }>({
    method: "POST",
    path: `${API_PREFIX}/erp/projects/${encodeURIComponent(id)}/restart`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Redémarrage impossible."));
  }
}

export const COMPANY_SIZE_OPTIONS: Array<{
  id: CompanySize;
  label: string;
  icon: string;
  description: string;
}> = [
  { id: "solo", label: "Juste moi", icon: "🧑", description: "Auto-entrepreneur" },
  { id: "small", label: "Petite équipe", icon: "👥", description: "2 à 10 personnes" },
  { id: "medium", label: "Une PME", icon: "🏢", description: "10 à 50 personnes" },
  { id: "large", label: "Grande entreprise", icon: "🏭", description: "50+ personnes" },
];

export const BUDGET_OPTIONS: Array<{
  id: Budget;
  label: string;
  icon: string;
}> = [
  { id: "low", label: "Moins de 3 000 €", icon: "💚" },
  { id: "medium", label: "Entre 3 000 € et 8 000 €", icon: "💛" },
  { id: "high", label: "Plus de 8 000 €", icon: "💎" },
];

export const MODULE_OPTIONS: Array<{
  id: ErpModuleId;
  label: string;
  icon: string;
}> = [
  { id: "facturation", label: "Facturation & devis", icon: "📄" },
  { id: "stocks", label: "Gestion des stocks", icon: "📦" },
  { id: "rh", label: "Gestion RH & employés", icon: "👤" },
  { id: "crm", label: "Ventes & CRM", icon: "🛒" },
  { id: "projets", label: "Gestion de projets", icon: "🔧" },
  { id: "comptabilite", label: "Comptabilité complète", icon: "📊" },
];

export const ERP_TYPE_LABELS: Record<ErpType, string> = {
  odoo: "Odoo 17",
  erpnext: "ERPNext 15",
  custom: "ERP Custom",
};
