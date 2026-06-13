import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

const PIPELINE = `${API_PREFIX}/pipeline`;

export type ProspectStatut =
  | "nouveau"
  | "contacté"
  | "démo_envoyée"
  | "négociation"
  | "gagné"
  | "perdu";

export const PROSPECT_STATUTS: ProspectStatut[] = [
  "nouveau",
  "contacté",
  "démo_envoyée",
  "négociation",
  "gagné",
  "perdu",
];

export const STATUT_LABELS: Record<ProspectStatut, string> = {
  nouveau: "Nouveau",
  contacté: "Contacté",
  démo_envoyée: "Démo envoyée",
  négociation: "Négociation",
  gagné: "Gagné",
  perdu: "Perdu",
};

export const STATUT_COLUMN_LABELS: Record<ProspectStatut, string> = {
  nouveau: "NOUVEAU",
  contacté: "CONTACTÉ",
  démo_envoyée: "DÉMO ENVOYÉE",
  négociation: "NÉGOCIATION",
  gagné: "GAGNÉ",
  perdu: "PERDU",
};

export const STATUT_HEADER_COLORS: Record<ProspectStatut, string> = {
  nouveau: "border-white/20 bg-white/5 text-white/60",
  contacté: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  démo_envoyée: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  négociation: "border-purple-500/30 bg-purple-500/10 text-purple-300",
  gagné: "border-teal-500/30 bg-teal-500/10 text-teal-300",
  perdu: "border-red-500/20 bg-red-500/5 text-red-300/60",
};

export const PROSPECT_SOURCES = [
  "manuel",
  "référence",
  "linkedin",
  "site web",
  "autre",
] as const;

export const INTERACTION_TYPES = [
  "appel",
  "email",
  "démo",
  "relance",
  "note",
] as const;

export interface Prospect {
  id: string;
  organization_id?: string;
  nom: string;
  entreprise: string | null;
  email: string | null;
  telephone: string | null;
  secteur: string | null;
  source: string;
  statut: ProspectStatut;
  valeur_estimee: number;
  notes: string | null;
  demo_url: string | null;
  contact_date: string | null;
  relance_date: string | null;
  closed_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProspectInteraction {
  id: string;
  prospect_id: string;
  type: string;
  notes: string | null;
  created_at: string;
}

export interface PipelineStats {
  par_statut: Record<string, { count: number; valeur: number }>;
  total_prospects: number;
  valeur_pipeline: number;
  taux_conversion: number;
  prospects_ce_mois: number;
}

export interface CreateProspectInput {
  nom: string;
  entreprise?: string;
  email?: string;
  telephone?: string;
  secteur?: string;
  source?: string;
  valeur_estimee?: number;
  notes?: string;
}

export function nextStatut(current: ProspectStatut): ProspectStatut | null {
  const idx = PROSPECT_STATUTS.indexOf(current);
  if (idx < 0 || idx >= PROSPECT_STATUTS.length - 1) return null;
  return PROSPECT_STATUTS[idx + 1];
}

export function formatEuro(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export async function fetchProspects(
  statut?: ProspectStatut,
): Promise<Prospect[]> {
  const q = statut ? `?statut=${encodeURIComponent(statut)}` : "";
  const res = await apiRequest<Prospect[]>({
    method: "GET",
    path: `${PIPELINE}/prospects${q}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les prospects."));
  }
  return Array.isArray(res.data) ? res.data : [];
}

export async function createProspect(
  data: CreateProspectInput,
): Promise<Prospect> {
  const res = await apiRequest<Prospect>({
    method: "POST",
    path: `${PIPELINE}/prospects`,
    body: data,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Création prospect impossible."));
  }
  return res.data;
}

export async function updateProspect(
  id: string,
  data: Partial<CreateProspectInput> & { notes?: string; demo_url?: string },
): Promise<Prospect> {
  const res = await apiRequest<Prospect>({
    method: "PATCH",
    path: `${PIPELINE}/prospects/${encodeURIComponent(id)}`,
    body: data,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Mise à jour impossible."));
  }
  return res.data;
}

export async function moveStatut(
  id: string,
  statut: ProspectStatut,
): Promise<Prospect> {
  const res = await apiRequest<Prospect>({
    method: "PATCH",
    path: `${PIPELINE}/prospects/${encodeURIComponent(id)}/statut`,
    body: { statut },
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Changement de statut impossible."));
  }
  return res.data;
}

export async function deleteProspect(id: string): Promise<void> {
  const res = await apiRequest<{ ok?: boolean }>({
    method: "DELETE",
    path: `${PIPELINE}/prospects/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Suppression impossible."));
  }
}

export async function fetchInteractions(
  prospectId: string,
): Promise<ProspectInteraction[]> {
  const res = await apiRequest<ProspectInteraction[]>({
    method: "GET",
    path: `${PIPELINE}/prospects/${encodeURIComponent(prospectId)}/interactions`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Interactions indisponibles."));
  }
  return Array.isArray(res.data) ? res.data : [];
}

export async function addInteraction(
  prospectId: string,
  type: string,
  notes?: string,
): Promise<ProspectInteraction> {
  const res = await apiRequest<ProspectInteraction>({
    method: "POST",
    path: `${PIPELINE}/prospects/${encodeURIComponent(prospectId)}/interactions`,
    body: { type, notes },
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Ajout interaction impossible."));
  }
  return res.data;
}

export async function fetchStats(): Promise<PipelineStats> {
  const res = await apiRequest<PipelineStats>({
    method: "GET",
    path: `${PIPELINE}/stats`,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Statistiques indisponibles."));
  }
  return res.data;
}
