import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export interface PostResult {
  success: boolean;
  post: string;
  accroche: string;
  conseil: string;
  format: string;
  label: string;
}

export interface HashtagsResult {
  success: boolean;
  hashtags: string[];
  conseil: string;
}

export interface BioResult {
  success: boolean;
  bios: { version: string; texte: string }[];
  format: string;
  limite: string;
}

export interface FormatInfo {
  id: string;
  label: string;
  ton: string;
  longueur: string;
}

export async function fetchFormats(): Promise<{
  formats: FormatInfo[];
  secteurs: string[];
}> {
  const res = await fetch(`${API_BASE}/api/content/formats`);
  return res.json();
}

export async function generatePost(params: {
  sujet: string;
  secteur: string;
  format_reseau: string;
  ton_personnalise?: string;
  nom_entreprise?: string;
}): Promise<PostResult> {
  const res = await fetch(`${API_BASE}/api/content/post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function generateHashtags(params: {
  sujet: string;
  secteur: string;
  format_reseau: string;
  nb_hashtags?: number;
}): Promise<HashtagsResult> {
  const res = await fetch(`${API_BASE}/api/content/hashtags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function generateBio(params: {
  nom_entreprise: string;
  secteur: string;
  valeur_ajoutee: string;
  format_reseau: string;
}): Promise<BioResult> {
  const res = await fetch(`${API_BASE}/api/content/bio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export interface CapcoreSubject {
  key: string;
  label: string;
}

export interface CapcorePostResult {
  success: boolean;
  post?: string;
  accroche?: string;
  conseil?: string;
  hashtags?: string[];
  format?: string;
  sujet?: string;
  error?: string;
}

export async function fetchCapcoreSubjects(): Promise<CapcoreSubject[]> {
  const res = await fetch(`${API_BASE}/api/content/capcore-subjects`);
  const data = await res.json();
  return data.subjects || [];
}

export async function generateCapcorePost(
  sujet_type: string,
  format_reseau: string,
  angle: string = "",
): Promise<CapcorePostResult> {
  const res = await fetch(`${API_BASE}/api/content/capcore-post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sujet_type, format_reseau, angle }),
  });
  return res.json();
}

export interface AssistFieldRequest {
  field_type: string;
  context: string;
  current_value?: string;
}

export interface AssistFieldResponse {
  suggestion: string;
}

export async function assistField(params: AssistFieldRequest): Promise<string> {
  const res = await apiRequest<AssistFieldResponse>({
    method: "POST",
    path: `${API_PREFIX}/content/assist`,
    body: {
      field_type: params.field_type,
      context: params.context,
      current_value: params.current_value ?? "",
    },
  });
  if (!res.ok || !res.data?.suggestion) {
    throw new Error(apiErrorMessage(res, "Assistance IA indisponible."));
  }
  return res.data.suggestion;
}
