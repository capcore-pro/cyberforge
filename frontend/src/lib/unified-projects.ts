import { API_PREFIX } from "@shared/constants";
import type {
  GenerationMode,
  ManagedProjectRecord,
  ProjectDetailResponse,
  ProjectRecord,
  ProjectType,
} from "@shared/types";
import { apiRequest } from "@/lib/api-client";
import type { DeletionReport, DeletionReportItem } from "@/lib/deletion-report";
import { hardDeleteApplicationWeb, listApplicationWeb } from "@/lib/application-web-api";
import { deleteClientDemo, findDemoIdByGeneration } from "@/lib/demos-api";
import { hardDeleteEcommerce, listEcommerce } from "@/lib/ecommerce-api";
import { hardDeleteExtension, listExtensions } from "@/lib/extensions-api";
import { deleteProject, duplicateSupabaseProject, updateManagedProjectTitle, updateProject } from "@/lib/projects-api";
import { updateDemoClient } from "@/lib/demos-api";
import { createVitrine, updateVitrine } from "@/lib/vitrines-api";
import { createApplicationWeb, updateApplicationWeb } from "@/lib/application-web-api";
import { createEcommerce, updateEcommerce } from "@/lib/ecommerce-api";
import { createReservationSite } from "@/lib/site-reservation-api";
import { createExtension, updateExtension } from "@/lib/extensions-api";
import { buildModificationPipelinePrompt } from "@/lib/project-modification";
import { streamCoremindRun } from "@/lib/pipeline-stream";
import { isOpenHandsEnabled } from "@/lib/openhands-preferences";
import { isPlaywrightEnabled } from "@/lib/playwright-preferences";
import { isLighthouseEnabled } from "@/lib/lighthouse-preferences";
import { isResearchEnabled } from "@/lib/research-preferences";
import { hardDeleteReservationSite, listReservationSites } from "@/lib/site-reservation-api";
import { hardDeleteVitrine, listVitrines } from "@/lib/vitrines-api";

export type UnifiedProjectType =
  | "vitrine"
  | "app_web"
  | "ecommerce"
  | "reservation"
  | "extension";

export type UnifiedProjectStatus = "online" | "offline" | "demo";

export type UnifiedProjectSource =
  | "managed_vitrine"
  | "managed_app_web"
  | "managed_ecommerce"
  | "managed_reservation"
  | "managed_extension"
  | "supabase";

export interface UnifiedProject {
  key: string;
  name: string;
  type: UnifiedProjectType;
  status: UnifiedProjectStatus;
  url: string | null;
  createdAt: string;
  prompt: string;
  source: UnifiedProjectSource;
  managedId?: string;
  supabaseProjectId?: string;
  demoId?: string;
  generationId?: string;
  clientId?: string | null;
  projectType?: ProjectType;
  generationMode?: GenerationMode;
}

export type UnifiedProjectTypeFilter = "all" | UnifiedProjectType;
export type UnifiedProjectStatusFilter = "all" | UnifiedProjectStatus;

export const TYPE_FILTER_OPTIONS: { id: UnifiedProjectTypeFilter; label: string }[] = [
  { id: "all", label: "Tous" },
  { id: "vitrine", label: "Vitrine" },
  { id: "app_web", label: "App web" },
  { id: "ecommerce", label: "E-commerce" },
  { id: "reservation", label: "Réservation" },
  { id: "extension", label: "Extension" },
];

export const STATUS_FILTER_OPTIONS: { id: UnifiedProjectStatusFilter; label: string }[] = [
  { id: "all", label: "Tous" },
  { id: "online", label: "En ligne" },
  { id: "offline", label: "Hors ligne" },
  { id: "demo", label: "Démo" },
];

export const TYPE_LABELS: Record<UnifiedProjectType, string> = {
  vitrine: "Vitrine",
  app_web: "App web",
  ecommerce: "E-commerce",
  reservation: "Réservation",
  extension: "Extension",
};

export const STATUS_LABELS: Record<UnifiedProjectStatus, string> = {
  online: "En ligne",
  offline: "Hors ligne",
  demo: "Démo",
};

function managedTypeFromRecord(record: ManagedProjectRecord): UnifiedProjectType {
  const t = record.type.toLowerCase();
  if (t.includes("extension")) return "extension";
  if (t.includes("ecommerce")) return "ecommerce";
  if (t.includes("reservation")) return "reservation";
  if (t.includes("application")) return "app_web";
  return "vitrine";
}

function managedStatus(record: ManagedProjectRecord): UnifiedProjectStatus {
  if (record.deleted_at) return "offline";
  if (record.status === "deployed" && Boolean(record.url_production?.trim())) {
    return "online";
  }
  return "offline";
}

function managedUrl(
  record: ManagedProjectRecord,
  source: UnifiedProjectSource,
): string | null {
  if (source === "managed_extension") {
    return `${API_PREFIX}/managed-projects/extensions/${record.id}/artifact.zip`;
  }
  return (
    record.url_production?.trim() ||
    record.url_preview?.trim() ||
    record.url_backend?.trim() ||
    null
  );
}

function managedGenerationMode(type: UnifiedProjectType): GenerationMode {
  if (type === "vitrine" || type === "reservation") return "vitrine_next";
  return "real_app";
}

function managedProjectType(type: UnifiedProjectType): ProjectType {
  switch (type) {
    case "app_web":
      return "application_web";
    case "extension":
      return "extension_navigateur";
    case "ecommerce":
      return "saas_dashboard";
    case "reservation":
      return "site_web";
    default:
      return "site_web";
  }
}

function mapManagedRecord(
  record: ManagedProjectRecord,
  source: UnifiedProjectSource,
): UnifiedProject | null {
  if (record.deleted_at) return null;
  const type = managedTypeFromRecord(record);
  return {
    key: `${source}:${record.id}`,
    name: record.title?.trim() || record.slug || "Sans titre",
    type,
    status: managedStatus(record),
    url: managedUrl(record, source),
    createdAt: record.created_at,
    prompt: record.prompt_last?.trim() || record.prompt_original?.trim() || "",
    source,
    managedId: record.id,
    projectType: managedProjectType(type),
    generationMode: managedGenerationMode(type),
  };
}

function supabaseProjectType(projectType: ProjectType): UnifiedProjectType {
  switch (projectType) {
    case "application_web":
      return "app_web";
    case "extension_navigateur":
      return "extension";
    case "saas_dashboard":
      return "ecommerce";
    default:
      return "vitrine";
  }
}

async function fetchProjectDetail(projectId: string) {
  return apiRequest<ProjectDetailResponse>({
    method: "GET",
    path: `${API_PREFIX}/projects/${projectId}`,
  });
}

async function mapSupabaseProject(project: ProjectRecord): Promise<UnifiedProject> {
  const type = supabaseProjectType(project.project_type);
  let status: UnifiedProjectStatus = "offline";
  let url: string | null = null;
  let demoId: string | undefined;
  let generationId: string | undefined;
  let clientId: string | null | undefined;
  let prompt = project.prompt?.trim() || "";

  const detail = await fetchProjectDetail(project.id);
  const latestGen = detail.ok ? detail.data?.generations?.[0] : undefined;
  if (latestGen) {
    generationId = latestGen.id;
    prompt = latestGen.prompt?.trim() || prompt;
    const demoLookup = await findDemoIdByGeneration(latestGen.id);
    if (demoLookup.ok && demoLookup.data?.demo_id) {
      demoId = demoLookup.data.demo_id;
      clientId = demoLookup.data.client_id ?? null;
      status = "demo";
      url =
        demoLookup.data.url?.trim() ||
        demoLookup.data.unlock_url?.trim() ||
        null;
    }
  }

  return {
    key: `supabase:${project.id}`,
    name: project.title?.trim() || "Sans titre",
    type,
    status,
    url,
    createdAt: project.created_at,
    prompt,
    source: "supabase",
    supabaseProjectId: project.id,
    demoId,
    generationId,
    clientId,
    projectType: project.project_type,
    generationMode: status === "demo" ? "client_demo" : "real_app",
  };
}

export async function loadAllUnifiedProjects(): Promise<UnifiedProject[]> {
  const [
    vitrinesRes,
    appsRes,
    ecommerceRes,
    reservationRes,
    extensionsRes,
    supabaseRes,
  ] = await Promise.all([
    listVitrines(),
    listApplicationWeb(),
    listEcommerce(),
    listReservationSites(),
    listExtensions(),
    apiRequest<ProjectRecord[]>({ method: "GET", path: `${API_PREFIX}/projects` }),
  ]);

  const managed: UnifiedProject[] = [];
  if (vitrinesRes.ok && Array.isArray(vitrinesRes.data)) {
    for (const row of vitrinesRes.data) {
      const mapped = mapManagedRecord(row, "managed_vitrine");
      if (mapped) managed.push(mapped);
    }
  }
  if (appsRes.ok && Array.isArray(appsRes.data)) {
    for (const row of appsRes.data) {
      const mapped = mapManagedRecord(row, "managed_app_web");
      if (mapped) managed.push(mapped);
    }
  }
  if (ecommerceRes.ok && Array.isArray(ecommerceRes.data)) {
    for (const row of ecommerceRes.data) {
      const mapped = mapManagedRecord(row, "managed_ecommerce");
      if (mapped) managed.push(mapped);
    }
  }
  if (reservationRes.ok && Array.isArray(reservationRes.data)) {
    for (const row of reservationRes.data) {
      const mapped = mapManagedRecord(row, "managed_reservation");
      if (mapped) managed.push(mapped);
    }
  }
  if (extensionsRes.ok && Array.isArray(extensionsRes.data)) {
    for (const row of extensionsRes.data) {
      const mapped = mapManagedRecord(row, "managed_extension");
      if (mapped) managed.push(mapped);
    }
  }

  const supabaseProjects =
    supabaseRes.ok && Array.isArray(supabaseRes.data) ? supabaseRes.data : [];
  const supabaseMapped = await Promise.all(
    supabaseProjects.map((p) => mapSupabaseProject(p)),
  );

  const managedSlugs = new Set(
    managed.map((p) => p.name.toLowerCase()).filter(Boolean),
  );

  const dedupedSupabase = supabaseMapped.filter((p) => {
    if (p.status !== "demo" && managedSlugs.has(p.name.toLowerCase())) {
      return false;
    }
    return true;
  });

  return [...managed, ...dedupedSupabase].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function filterUnifiedProjects(
  projects: UnifiedProject[],
  typeFilter: UnifiedProjectTypeFilter,
  statusFilter: UnifiedProjectStatusFilter,
  search: string,
): UnifiedProject[] {
  const q = search.trim().toLowerCase();
  return projects.filter((p) => {
    if (typeFilter !== "all" && p.type !== typeFilter) return false;
    if (statusFilter !== "all" && p.status !== statusFilter) return false;
    if (q && !p.name.toLowerCase().includes(q)) return false;
    return true;
  });
}

export async function deleteUnifiedProject(project: UnifiedProject): Promise<{
  ok: boolean;
  error?: string;
  report?: DeletionReport;
}> {
  try {
    switch (project.source) {
      case "managed_vitrine": {
        if (!project.managedId) return { ok: false, error: "Identifiant manquant." };
        const res = await hardDeleteVitrine(project.managedId);
        if (!res.ok || !res.data) {
          return { ok: false, error: "Échec suppression vitrine." };
        }
        return { ok: res.data.ok ?? true, report: res.data };
      }
      case "managed_app_web": {
        if (!project.managedId) return { ok: false, error: "Identifiant manquant." };
        const res = await hardDeleteApplicationWeb(project.managedId);
        if (!res.ok || !res.data) {
          return { ok: false, error: "Échec suppression application web." };
        }
        return { ok: res.data.ok ?? true, report: res.data };
      }
      case "managed_ecommerce": {
        if (!project.managedId) return { ok: false, error: "Identifiant manquant." };
        const res = await hardDeleteEcommerce(project.managedId);
        if (!res.ok || !res.data) {
          return { ok: false, error: "Échec suppression e-commerce." };
        }
        return { ok: res.data.ok ?? true, report: res.data };
      }
      case "managed_reservation": {
        if (!project.managedId) return { ok: false, error: "Identifiant manquant." };
        const res = await hardDeleteReservationSite(project.managedId);
        if (!res.ok || !res.data) {
          return { ok: false, error: "Échec suppression réservation." };
        }
        return { ok: res.data.ok ?? true, report: res.data };
      }
      case "managed_extension": {
        if (!project.managedId) return { ok: false, error: "Identifiant manquant." };
        const res = await hardDeleteExtension(project.managedId);
        if (!res.ok || !res.data) {
          return { ok: false, error: "Échec suppression extension." };
        }
        return { ok: res.data.ok ?? true, report: res.data };
      }
      case "supabase": {
        if (!project.supabaseProjectId) {
          return { ok: false, error: "Identifiant manquant." };
        }
        const items: DeletionReportItem[] = [];
        if (project.demoId) {
          const demoDel = await deleteClientDemo(project.demoId);
          items.push({
            label: "Cloudflare démo",
            status: demoDel.ok ? "ok" : "error",
            detail: demoDel.ok ? undefined : "Échec suppression démo",
          });
        }
        const projDel = await deleteProject(project.supabaseProjectId);
        items.push({
          label: "Supabase",
          status: projDel.ok ? "ok" : "error",
          detail: projDel.ok ? "projects + generations" : "Échec suppression",
        });
        const report: DeletionReport = {
          deleted: true,
          ok: items.every((i) => i.status !== "error"),
          items,
        };
        return { ok: report.ok, report };
      }
      default:
        return { ok: false, error: "Type de projet inconnu." };
    }
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "Erreur inattendue.",
    };
  }
}

export function openProjectUrl(url: string) {
  const target = url.startsWith("http") ? url : `${window.location.origin}${url}`;
  window.open(target, "_blank", "noopener,noreferrer");
}

export async function renameUnifiedProject(
  project: UnifiedProject,
  name: string,
): Promise<{ ok: boolean; error?: string }> {
  const trimmed = name.trim();
  if (!trimmed) {
    return { ok: false, error: "Le nom du projet est requis." };
  }

  if (project.source === "supabase" && project.supabaseProjectId) {
    const res = await updateProject(project.supabaseProjectId, { title: trimmed });
    return res.ok ? { ok: true } : { ok: false, error: "Échec mise à jour du nom." };
  }

  if (project.managedId) {
    const res = await updateManagedProjectTitle(project.managedId, trimmed);
    return res.ok ? { ok: true } : { ok: false, error: "Échec mise à jour du nom." };
  }

  return { ok: false, error: "Projet non modifiable." };
}

export async function affiliateUnifiedProjectClient(
  project: UnifiedProject,
  clientId: string | null,
): Promise<{ ok: boolean; error?: string }> {
  if (!project.demoId) {
    return {
      ok: false,
      error: "Association client disponible uniquement pour les projets avec démo.",
    };
  }
  const res = await updateDemoClient(project.demoId, clientId);
  return res.ok ? { ok: true } : { ok: false, error: "Échec association client." };
}

function managedUpdateFn(project: UnifiedProject) {
  if (!project.managedId) return null;
  switch (project.source) {
    case "managed_vitrine":
      return (prompt: string) => updateVitrine(project.managedId!, prompt);
    case "managed_app_web":
      return (prompt: string) => updateApplicationWeb(project.managedId!, prompt);
    case "managed_ecommerce":
      return (prompt: string) => updateEcommerce(project.managedId!, prompt);
    case "managed_extension":
      return (prompt: string) => updateExtension(project.managedId!, prompt);
    default:
      return null;
  }
}

function managedCreateFn(project: UnifiedProject) {
  const prompt = project.prompt;
  switch (project.source) {
    case "managed_vitrine":
      return () => createVitrine(prompt);
    case "managed_app_web":
      return () => createApplicationWeb(prompt);
    case "managed_ecommerce":
      return () => createEcommerce(prompt);
    case "managed_reservation":
      return () => createReservationSite(prompt);
    case "managed_extension":
      return () => createExtension(prompt);
    default:
      return null;
  }
}

export async function modifyUnifiedProject(
  project: UnifiedProject,
  modificationPrompt: string,
  projectName: string,
): Promise<{ ok: boolean; error?: string }> {
  const { prompt, inspirationBrief } = buildModificationPipelinePrompt(
    modificationPrompt,
    projectName,
    project.prompt,
  );

  const updater = managedUpdateFn(project);
  if (updater) {
    const composed = `${inspirationBrief}\n\nPrompt utilisateur :\n${prompt}`;
    const res = await updater(composed);
    return res.ok
      ? { ok: true }
      : { ok: false, error: "Échec de la modification du projet géré." };
  }

  const res = await streamCoremindRun({
    prompt,
    project_type: project.projectType ?? "site_web",
    generation_mode: project.generationMode ?? "client_demo",
    inspiration_brief: inspirationBrief,
    openhands_enabled: isOpenHandsEnabled(),
    playwright_enabled: isPlaywrightEnabled(),
    lighthouse_enabled: isLighthouseEnabled(),
    research_enabled: isResearchEnabled(),
  });

  if (!res.ok) {
    return {
      ok: false,
      error: res.statusText || "Échec du pipeline de modification.",
    };
  }

  if (projectName.trim() && project.supabaseProjectId) {
    await updateProject(project.supabaseProjectId, { title: projectName.trim() });
  }

  return { ok: true };
}

export async function duplicateUnifiedProject(
  project: UnifiedProject,
): Promise<{ ok: boolean; project?: UnifiedProject; error?: string }> {
  const copyName = `Copie de ${project.name}`;

  if (project.source === "supabase" && project.supabaseProjectId) {
    const res = await duplicateSupabaseProject(project.supabaseProjectId);
    if (!res.ok || !res.data) {
      return { ok: false, error: "Échec duplication Supabase." };
    }
    const mapped = await mapSupabaseProject(res.data.project);
    if (copyName !== mapped.name) {
      await updateProject(res.data.project.id, { title: copyName });
      mapped.name = copyName;
    }
    return { ok: true, project: mapped };
  }

  const creator = managedCreateFn(project);
  if (!creator || !project.managedId) {
    return { ok: false, error: "Duplication non supportée pour ce type." };
  }

  const res = await creator();
  const created = res.data?.project as ManagedProjectRecord | undefined;
  if (!res.ok || !created?.id) {
    return { ok: false, error: "Échec duplication du projet géré." };
  }

  await updateManagedProjectTitle(created.id, copyName);
  const mapped = mapManagedRecord(created, project.source);
  if (!mapped) {
    return { ok: false, error: "Projet dupliqué introuvable." };
  }
  return { ok: true, project: { ...mapped, name: copyName } };
}
