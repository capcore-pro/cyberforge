import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const TOOLBOX = `${API_PREFIX}/toolbox`;

export interface SectorPalette {
  primary: string;
  secondary: string;
  accent: string;
}

export interface SectorTypography {
  heading: string;
  body: string;
}

export interface SectorData {
  nom: string;
  palette: SectorPalette;
  typo: SectorTypography;
  composants: string[];
  mots_cles_visuels: string[];
}

export interface ToolboxPhoto {
  id: string;
  url_thumb: string;
  url_full: string;
  url_download: string;
  source: string;
  author: string | null;
  author_url: string | null;
}

export interface ToolboxIcon {
  name: string;
  svg_url: string;
  prefix: string;
  icon: string;
}

export interface ToolboxIllustration {
  id: string;
  title: string;
  svg_url: string;
}

export interface ToolboxComposant {
  id: string;
  label: string;
  description: string;
  categorie: string;
  snippet: string;
  dependances: string[];
}

export interface SeoMetaPayload {
  secteur: string;
  nom_entreprise: string;
  ville: string;
  description_courte: string;
}

export interface SeoMetaResult {
  title: string;
  meta_description: string;
  og_title: string;
  og_description: string;
  keywords: string[];
  schema_org: Record<string, unknown>;
}

export function fetchToolboxSecteurs() {
  return apiRequest<{ secteurs: SectorData[] }>({
    method: "GET",
    path: `${TOOLBOX}/secteurs`,
  });
}

export function fetchToolboxComposants() {
  return apiRequest<{ composants: ToolboxComposant[] }>({
    method: "GET",
    path: `${TOOLBOX}/composants`,
  });
}

export function searchToolboxPhotos(params: {
  query?: string;
  secteur?: string;
  per_page?: number;
}) {
  const q = new URLSearchParams();
  if (params.query?.trim()) q.set("query", params.query.trim());
  if (params.secteur?.trim()) q.set("secteur", params.secteur.trim());
  if (params.per_page) q.set("per_page", String(params.per_page));
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<{ query: string; secteur: string | null; photos: ToolboxPhoto[] }>({
    method: "GET",
    path: `${TOOLBOX}/photos${suffix}`,
    timeoutMs: 60_000,
  });
}

export function searchToolboxIcones(params: { query?: string; limit?: number }) {
  const q = new URLSearchParams();
  if (params.query?.trim()) q.set("query", params.query.trim());
  if (params.limit) q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<{ query: string; icones: ToolboxIcon[] }>({
    method: "GET",
    path: `${TOOLBOX}/icones${suffix}`,
  });
}

export function searchToolboxIllustrations(params: { query?: string; limit?: number }) {
  const q = new URLSearchParams();
  if (params.query?.trim()) q.set("query", params.query.trim());
  if (params.limit) q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<{ query: string; illustrations: ToolboxIllustration[] }>({
    method: "GET",
    path: `${TOOLBOX}/illustrations${suffix}`,
    timeoutMs: 60_000,
  });
}

export function generateToolboxSeoMeta(body: SeoMetaPayload) {
  return apiRequest<SeoMetaResult>({
    method: "POST",
    path: `${TOOLBOX}/seo-meta`,
    body,
    timeoutMs: 90_000,
  });
}

export interface ApplyPalettePayload {
  project_id: string;
  palette: SectorPalette;
  typo?: SectorTypography;
  secteur?: string;
}

export interface ApplyPaletteResult {
  scheduled: boolean;
  run_id: string;
  message: string;
}

export function applyToolboxPalette(body: ApplyPalettePayload) {
  return apiRequest<ApplyPaletteResult>({
    method: "POST",
    path: `${TOOLBOX}/apply-palette`,
    body,
    timeoutMs: 30_000,
  });
}
