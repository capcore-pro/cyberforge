import type { GenerationMode, ProjectType } from "@shared/types";

export type GeneratorKindId =
  | "vitrine"
  | "app_web"
  | "ecommerce"
  | "reservation"
  | "extension"
  | "desktop";

export const GENERATOR_KIND_IDS: GeneratorKindId[] = [
  "vitrine",
  "app_web",
  "ecommerce",
  "reservation",
  "extension",
  "desktop",
];

const GENERATOR_KIND_STORAGE_KEY = "cyberforge.generatorKind";

export function isGeneratorKindId(value: string): value is GeneratorKindId {
  return (GENERATOR_KIND_IDS as string[]).includes(value);
}

/** Mémorise le type choisi à l'étape 1 (vitrine ≠ réservation malgré le même projectType). */
export function persistGeneratorKind(kind: GeneratorKindId): void {
  try {
    localStorage.setItem(GENERATOR_KIND_STORAGE_KEY, kind);
  } catch {
    /* quota / mode privé */
  }
}

export function readStoredGeneratorKind(): GeneratorKindId | null {
  try {
    const raw = localStorage.getItem(GENERATOR_KIND_STORAGE_KEY);
    if (raw && isGeneratorKindId(raw)) return raw;
  } catch {
    /* indisponible */
  }
  return null;
}

export type DeployMode = "demo" | "real";

export interface GeneratorKindOption {
  id: GeneratorKindId;
  icon: string;
  title: string;
  description: string;
  projectType: ProjectType;
  defaultDescription?: string;
  examples: string[];
}

/** Icônes et couleurs premium — étape 1 du générateur. */
export const GENERATOR_KIND_VISUAL: Record<
  GeneratorKindId,
  {
    emoji: string;
    colorClass: string;
    ringClass: string;
    shortDescription: string;
  }
> = {
  vitrine: {
    emoji: "🏪",
    colorClass: "text-amber-300",
    ringClass: "ring-amber-400/30",
    shortDescription: "Site vitrine multi-pages pour présenter une activité.",
  },
  app_web: {
    emoji: "💻",
    colorClass: "text-blue-300",
    ringClass: "ring-blue-400/30",
    shortDescription: "Application web avec logique métier et données.",
  },
  ecommerce: {
    emoji: "🛒",
    colorClass: "text-emerald-300",
    ringClass: "ring-emerald-400/30",
    shortDescription: "Boutique en ligne, panier et paiement.",
  },
  reservation: {
    emoji: "📅",
    colorClass: "text-violet-300",
    ringClass: "ring-violet-400/30",
    shortDescription: "Agenda en ligne, créneaux et confirmations.",
  },
  extension: {
    emoji: "🔌",
    colorClass: "text-cyan-300",
    ringClass: "ring-cyan-400/30",
    shortDescription: "Extension Chrome ou Firefox.",
  },
  desktop: {
    emoji: "🖥️",
    colorClass: "text-orange-300",
    ringClass: "ring-orange-400/30",
    shortDescription: "Logiciel Windows (.exe) pour artisans.",
  },
};

export const GENERATOR_KINDS: GeneratorKindOption[] = [
  {
    id: "vitrine",
    icon: "◆",
    title: "Vitrine",
    description: "Site multi-pages pour présenter votre activité",
    projectType: "site_web",
    examples: [
      "Site vitrine pour une boulangerie artisanale à Nantes, ton chaleureux, couleurs chaudes",
      "Cabinet d'architecte : portfolio de réalisations, équipe et contact",
      "Salon de coiffure : prestations, tarifs, galerie avant/après et prise de rendez-vous",
    ],
  },
  {
    id: "app_web",
    icon: "▣",
    title: "App web",
    description: "Application avec base de données et logique métier",
    projectType: "application_web",
    examples: [
      "CRM simple pour artisans : clients, devis, suivi des chantiers",
      "Tableau de bord pour gérer des stocks et alertes de réapprovisionnement",
      "Portail interne avec authentification et rôles administrateur / employé",
    ],
  },
  {
    id: "ecommerce",
    icon: "▧",
    title: "E-commerce",
    description: "Boutique en ligne avec panier et paiement",
    projectType: "saas_dashboard",
    defaultDescription:
      "Boutique en ligne avec catalogue produits, panier et paiement Stripe.",
    examples: [
      "Boutique de cosmétiques naturels avec filtres par peau et livraison France",
      "Vente de vins en ligne : fiches produit, panier et checkout sécurisé",
      "Marketplace locale pour producteurs : catégories, avis clients et paiement",
    ],
  },
  {
    id: "reservation",
    icon: "◷",
    title: "Réservation",
    description: "Agenda en ligne avec créneaux et paiement",
    projectType: "site_web",
    defaultDescription:
      "Site de réservation en ligne avec créneaux, services et confirmation.",
    examples: [
      "Réservation pour un restaurant : tables, menu du jour et confirmation SMS",
      "Prise de rendez-vous pour un ostéopathe avec créneaux et paiement en ligne",
      "Location de salles : calendrier, tarifs à l'heure et acompte Stripe",
    ],
  },
  {
    id: "extension",
    icon: "⬢",
    title: "Extension",
    description: "Plugin Chrome ou Firefox",
    projectType: "extension_navigateur",
    examples: [
      "Extension qui résume les pages web longues en quelques points clés",
      "Bloqueur de distractions avec liste blanche de sites professionnels",
      "Assistant qui remplit automatiquement les formulaires récurrents",
    ],
  },
  {
    id: "desktop",
    icon: "▤",
    title: "App desktop",
    description: "Logiciel Windows .exe pour artisans",
    projectType: "application_desktop",
    examples: [
      "Logiciel de facturation pour plombier : clients, devis PDF et relances",
      "Caisse enregistreuse offline pour commerce de proximité",
      "Suivi de chantier avec photos, notes et export Excel",
    ],
  },
];

export function getGeneratorKind(id: GeneratorKindId): GeneratorKindOption {
  return GENERATOR_KINDS.find((k) => k.id === id) ?? GENERATOR_KINDS[0];
}

export function resolveGenerationMode(
  kind: GeneratorKindId,
  deployMode: DeployMode,
): GenerationMode {
  if (deployMode === "demo") return "client_demo";
  if (kind === "vitrine" || kind === "reservation") return "vitrine_next";
  return "real_app";
}

export function inferKindFromSession(
  projectType: ProjectType,
  generationMode: GenerationMode,
  description: string,
): GeneratorKindId {
  const stored = readStoredGeneratorKind();
  if (stored) return stored;

  if (projectType === "application_desktop") return "desktop";
  if (projectType === "application_web") return "app_web";
  if (projectType === "saas_dashboard") return "ecommerce";
  if (projectType === "extension_navigateur") return "extension";
  if (projectType === "site_web" && generationMode === "vitrine_next") {
    const lower = description.toLowerCase();
    if (
      lower.includes("réservation") ||
      lower.includes("reservation") ||
      lower.includes("créneau") ||
      lower.includes("creneau") ||
      lower.includes("agenda")
    ) {
      return "reservation";
    }
    return "vitrine";
  }
  if (generationMode === "client_demo") return "vitrine";
  return "vitrine";
}

export function inferDeployModeFromSession(
  generationMode: GenerationMode,
): DeployMode {
  return generationMode === "client_demo" ? "demo" : "real";
}

/**
 * Préfixe TYPE: pour imposer la pricing_category côté ArchitectAI (démo template-first).
 */
export function buildGeneratorPipelinePrompt(
  kind: GeneratorKindId,
  prompt: string,
): string {
  const body = prompt.trim();
  if (!body) {
    return body;
  }
  if (kind === "reservation") {
    return `TYPE: site_reservation\n${body}`;
  }
  if (kind === "ecommerce") {
    return `TYPE: ecommerce\n${body}`;
  }
  if (kind === "extension") {
    return `TYPE: extension_navigateur\n${body}`;
  }
  return body;
}

export function syncSessionFromKind(
  kind: GeneratorKindId,
  deployMode: DeployMode,
): { projectType: ProjectType; generationMode: GenerationMode } {
  const option = getGeneratorKind(kind);
  return {
    projectType: option.projectType,
    generationMode: resolveGenerationMode(kind, deployMode),
  };
}

/** Secteurs proposés pour l’URL d’inspiration (clone / analyse). */
export const INSPIRATION_SECTOR_OPTIONS: { nom: string; label: string }[] = [
  { nom: "restauration", label: "Restauration" },
  { nom: "nautisme", label: "Nautisme" },
  { nom: "immobilier", label: "Immobilier" },
  { nom: "sante", label: "Santé" },
  { nom: "artisanat", label: "Artisanat" },
  { nom: "beaute", label: "Beauté" },
  { nom: "sport", label: "Sport" },
  { nom: "technologie", label: "Technologie" },
  { nom: "education", label: "Éducation" },
  { nom: "commerce", label: "Commerce" },
];

/** Secteur par défaut pour Firecrawl (clone / analyse). */
export function kindToToolboxSecteur(kind: GeneratorKindId): string {
  switch (kind) {
    case "reservation":
      return "restauration";
    case "ecommerce":
      return "commerce";
    case "app_web":
      return "technologie";
    case "extension":
      return "technologie";
    case "desktop":
      return "technologie";
    case "vitrine":
    default:
      return "commerce";
  }
}
