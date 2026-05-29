import type { GenerationMode, ProjectType } from "@shared/types";

export type GeneratorKindId =
  | "vitrine"
  | "app_web"
  | "ecommerce"
  | "reservation"
  | "extension"
  | "desktop";

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
