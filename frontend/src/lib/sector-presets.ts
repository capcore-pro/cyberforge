import type { ProjectType } from "@shared/types";
import {
  buildGeneratorPipelinePrompt,
  type GeneratorKindId,
} from "@/lib/generator-kinds";

export type SectorPresetId = string;

export interface SectorPreset {
  id: SectorPresetId;
  label: string;
  emoji: string;
  /** Types de projet auxquels ce secteur est proposé */
  kinds: GeneratorKindId[];
  project_type: string;
  couleur_primaire: string;
  couleur_secondaire: string;
  description: string;
  services: string[];
  sector: string;
}

export interface GeneratorDetailsForm {
  description: string;
  services: string[];
  couleur_primaire: string;
  couleur_secondaire: string;
  ville: string;
  phone: string;
  email: string;
  address: string;
  stripe_publishable_key: string;
}

export const EMPTY_GENERATOR_DETAILS: GeneratorDetailsForm = {
  description: "",
  services: [],
  couleur_primaire: "#c9a227",
  couleur_secondaire: "#1a1a2e",
  ville: "",
  phone: "",
  email: "",
  address: "",
  stripe_publishable_key: "",
};

/** Liste ordonnée — filtrer par kind via `listSectorsForKind`. */
export const SECTOR_PRESET_LIST: SectorPreset[] = [
  // —— Vitrine ——
  {
    id: "artisan-btp",
    label: "Artisan & BTP",
    emoji: "🏗️",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#b45309",
    couleur_secondaire: "#292524",
    description:
      "Artisan du bâtiment : interventions rapides, devis gratuits et savoir-faire local (plomberie, électricité, maçonnerie, peinture).",
    services: ["Dépannage urgent", "Devis gratuit", "Rénovation", "Installation", "Entretien"],
    sector: "artisan / BTP",
  },
  {
    id: "restaurant-cafe",
    label: "Restaurant & Café",
    emoji: "🍽️",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#9a3412",
    couleur_secondaire: "#1c1917",
    description:
      "Restaurant ou café de quartier : cuisine de saison, ambiance chaleureuse et réservation de table en ligne.",
    services: ["Carte du jour", "Brunch", "Privatisation", "Traiteur", "Click & collect"],
    sector: "restauration",
  },
  {
    id: "sante-bien-etre",
    label: "Santé & Bien-être",
    emoji: "⚕️",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#0d9488",
    couleur_secondaire: "#134e4a",
    description:
      "Cabinet de santé ou bien-être : prise de rendez-vous, accompagnement personnalisé et cadre apaisant.",
    services: ["Consultation", "Bilan", "Suivi", "Urgences", "Téléconsultation"],
    sector: "santé / bien-être",
  },
  {
    id: "nautique-marine",
    label: "Nautique & Marine",
    emoji: "⚓",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#0369a1",
    couleur_secondaire: "#0c4a6e",
    description:
      "Activité nautique : location, entretien bateau et services portuaires avec expertise locale.",
    services: ["Location bateau", "Entretien", "Formation", "Sorties guidées", "Hivernage"],
    sector: "nautique / marine",
  },
  {
    id: "immobilier-architecture",
    label: "Immobilier & Architecture",
    emoji: "🏠",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#1e3a5f",
    couleur_secondaire: "#0f172a",
    description:
      "Agence immobilière ou cabinet d'architecture : biens d'exception, visites virtuelles et accompagnement sur-mesure.",
    services: ["Vente", "Location", "Estimation", "Gestion locative", "Conseil achat"],
    sector: "immobilier / architecture",
  },
  {
    id: "beaute-coiffure",
    label: "Beauté & Coiffure",
    emoji: "💆",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#be185d",
    couleur_secondaire: "#4c0519",
    description:
      "Salon de coiffure ou institut beauté : prestations premium, galerie avant/après et réservation en ligne.",
    services: ["Coupe", "Coloration", "Soins", "Barbe", "Mariage"],
    sector: "beauté / coiffure",
  },
  {
    id: "formation-coaching",
    label: "Formation & Coaching",
    emoji: "🎓",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#4f46e5",
    couleur_secondaire: "#312e81",
    description:
      "Organisme de formation ou coach professionnel : programmes certifiants et accompagnement individualisé.",
    services: ["Formation intra", "Coaching individuel", "Ateliers", "Certification", "E-learning"],
    sector: "formation / coaching",
  },
  {
    id: "garage-auto",
    label: "Garage & Auto",
    emoji: "🔧",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#dc2626",
    couleur_secondaire: "#1f2937",
    description:
      "Garage automobile : entretien, réparation et contrôle technique avec devis transparent et pièces d'origine.",
    services: ["Révision", "Pneus", "Carrosserie", "Diagnostic", "Véhicule de courtoisie"],
    sector: "garage / automobile",
  },
  {
    id: "tourisme-loisirs",
    label: "Tourisme & Loisirs",
    emoji: "🌍",
    kinds: ["vitrine"],
    project_type: "vitrine",
    couleur_primaire: "#2d6a4f",
    couleur_secondaire: "#1b4332",
    description:
      "Site vitrine pour camping, gîte, hôtel ou activité touristique : présentation des hébergements, activités, tarifs et contact.",
    services: [
      "Présentation hébergements",
      "Activités & loisirs",
      "Tarifs & disponibilités",
      "Galerie photos",
      "Contact & réservation",
    ],
    sector: "tourisme / loisirs",
  },
  // —— Réservation ——
  {
    id: "camping-plein-air",
    label: "Camping & Plein air",
    emoji: "🏕️",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#2d6a4f",
    couleur_secondaire: "#1b4332",
    description:
      "Camping familial avec hébergements variés, animations et réservation en ligne pour séjours nature.",
    services: ["Mobil-homes", "Chalets", "Emplacements tente", "Piscine", "Animations"],
    sector: "camping / plein air",
  },
  {
    id: "hotel-hebergement",
    label: "Hôtel & Hébergement",
    emoji: "🏨",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#1d4ed8",
    couleur_secondaire: "#1e3a8a",
    description:
      "Hôtel ou établissement d'hébergement : chambres confort, petit-déjeuner et réservation directe.",
    services: ["Chambres standard", "Suites", "Petit-déjeuner", "Spa", "Séminaires"],
    sector: "hôtel / hébergement",
  },
  {
    id: "gite-location",
    label: "Gîte & Location saisonnière",
    emoji: "🏡",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#ca8a04",
    couleur_secondaire: "#713f12",
    description:
      "Gîtes et locations saisonnières : séjours authentiques, calendrier de disponibilités et réservation sécurisée.",
    services: ["Gîte 4 pers.", "Maison 8 pers.", "Week-end", "Semaine", "Options ménage"],
    sector: "gîte / location saisonnière",
  },
  {
    id: "restaurant-table",
    label: "Restaurant (réservation table)",
    emoji: "🍽️",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#7c2d12",
    couleur_secondaire: "#292524",
    description:
      "Restaurant avec réservation de tables en ligne : menu du jour, événements et confirmation instantanée.",
    services: ["Déjeuner", "Dîner", "Menu dégustation", "Privatisation", "Terrasse"],
    sector: "restauration / réservation",
  },
  {
    id: "spa-bien-etre-resa",
    label: "Spa & Bien-être",
    emoji: "💆",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#7c3aed",
    couleur_secondaire: "#4c1d95",
    description:
      "Spa et centre bien-être : soins, forfaits détente et réservation de créneaux en ligne.",
    services: ["Massage", "Soin visage", "Hammam", "Forfait duo", "Abonnement"],
    sector: "spa / bien-être",
  },
  {
    id: "activites-loisirs",
    label: "Activités & Loisirs",
    emoji: "🎯",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#ea580c",
    couleur_secondaire: "#7c2d12",
    description:
      "Centre d'activités et loisirs : réservation de sessions, groupes et événements outdoor ou indoor.",
    services: ["Session découverte", "Pack famille", "Anniversaire", "Team building", "Carte cadeau"],
    sector: "activités / loisirs",
  },
  {
    id: "location-nautique",
    label: "Location nautique",
    emoji: "🚤",
    kinds: ["reservation"],
    project_type: "site_reservation",
    couleur_primaire: "#0284c7",
    couleur_secondaire: "#0c4a6e",
    description:
      "Location nautique : bateaux, jet-skis et sorties en mer avec créneaux et tarifs transparents.",
    services: ["Bateau à moteur", "Voilier", "Jet-ski", "Sortie guidée", "Permis côtier"],
    sector: "nautique / location",
  },
  // —— E-commerce ——
  {
    id: "mode-vetements",
    label: "Mode & Vêtements",
    emoji: "👗",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#db2777",
    couleur_secondaire: "#831843",
    description:
      "Boutique mode en ligne : collections tendance, guides des tailles et livraison rapide.",
    services: ["Nouveautés", "Femme", "Homme", "Accessoires", "Soldes"],
    sector: "mode / vêtements",
  },
  {
    id: "artisan-createur",
    label: "Artisan & Créateur",
    emoji: "🎨",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#a16207",
    couleur_secondaire: "#44403c",
    description:
      "Boutique d'artisan créateur : pièces uniques, fabrication locale et vente directe producteur.",
    services: ["Pièces uniques", "Sur commande", "Coffrets cadeaux", "Atelier", "Personnalisation"],
    sector: "artisanat / créateur",
  },
  {
    id: "bio-alimentation",
    label: "Bio & Alimentation",
    emoji: "🌿",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#15803d",
    couleur_secondaire: "#14532d",
    description:
      "Épicerie bio et produits locaux : circuits courts, paniers composables et livraison à domicile.",
    services: ["Panier bio", "Fruits & légumes", "Épicerie sèche", "Produits laitiers", "Abonnement"],
    sector: "bio / alimentation",
  },
  {
    id: "hightech-electronique",
    label: "High-tech & Électronique",
    emoji: "💻",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#2563eb",
    couleur_secondaire: "#1e3a8a",
    description:
      "Boutique high-tech : électronique grand public, comparatifs produits et SAV réactif.",
    services: ["Smartphones", "Audio", "Gaming", "Accessoires", "Reprise"],
    sector: "high-tech / électronique",
  },
  {
    id: "maison-deco",
    label: "Maison & Déco",
    emoji: "🏠",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#78716c",
    couleur_secondaire: "#292524",
    description:
      "Décoration et ameublement en ligne : inspirations intérieur, nouveautés et livraison soignée.",
    services: ["Mobilier", "Luminaires", "Textile", "Cuisine", "Jardin"],
    sector: "maison / déco",
  },
  {
    id: "fleurs-cadeaux",
    label: "Fleurs & Cadeaux",
    emoji: "🌸",
    kinds: ["ecommerce"],
    project_type: "ecommerce",
    couleur_primaire: "#e11d48",
    couleur_secondaire: "#881337",
    description:
      "Fleuriste et cadeaux : bouquets sur-mesure, livraison le jour J et compositions événementielles.",
    services: ["Bouquets", "Mariage", "Deuil", "Plantes", "Coffrets cadeaux"],
    sector: "fleurs / cadeaux",
  },
  // —— App web ——
  {
    id: "dashboard-analytics",
    label: "Dashboard & Analytics",
    emoji: "📊",
    kinds: ["app_web"],
    project_type: "application_web",
    couleur_primaire: "#4f46e5",
    couleur_secondaire: "#1e1b4b",
    description:
      "Application web de pilotage : tableaux de bord, KPIs temps réel et exports pour décideurs.",
    services: ["Tableaux de bord", "Rapports PDF", "Alertes", "Multi-utilisateurs", "API"],
    sector: "dashboard / analytics",
  },
  {
    id: "crm-clients",
    label: "CRM & Clients",
    emoji: "👥",
    kinds: ["app_web"],
    project_type: "crm",
    couleur_primaire: "#0891b2",
    couleur_secondaire: "#164e63",
    description:
      "CRM métier : pipeline commercial, fiches clients enrichies et relances automatisées.",
    services: ["Contacts", "Devis", "Pipeline", "Relances", "Historique"],
    sector: "CRM / clients",
  },
  {
    id: "crm-immobilier",
    label: "CRM Immobilier",
    emoji: "🏠",
    kinds: ["crm"],
    project_type: "crm",
    couleur_primaire: "#0f766e",
    couleur_secondaire: "#134e4a",
    description:
      "CRM immobilier : biens, acquéreurs, visites et suivi des compromis jusqu'à l'acte.",
    services: ["Biens", "Prospects", "Visites", "Compromis", "Pipeline"],
    sector: "CRM / immobilier",
  },
  {
    id: "crm-recrutement",
    label: "CRM Recrutement",
    emoji: "🎯",
    kinds: ["crm"],
    project_type: "crm",
    couleur_primaire: "#7c3aed",
    couleur_secondaire: "#4c1d95",
    description:
      "CRM recrutement : candidats, offres, entretiens et pipeline d'intégration.",
    services: ["Candidats", "Offres", "Entretiens", "Pipeline", "Onboarding"],
    sector: "CRM / recrutement",
  },
  {
    id: "crm-agence",
    label: "CRM Agence",
    emoji: "✨",
    kinds: ["crm"],
    project_type: "crm",
    couleur_primaire: "#d4a843",
    couleur_secondaire: "#78350f",
    description:
      "CRM agence créative : clients, projets, devis et facturation centralisés.",
    services: ["Clients", "Projets", "Devis", "Factures", "Pipeline"],
    sector: "CRM / agence",
  },
  {
    id: "crm-coach",
    label: "CRM Coach / Consultant",
    emoji: "🧭",
    kinds: ["crm"],
    project_type: "crm",
    couleur_primaire: "#0ea5e9",
    couleur_secondaire: "#0c4a6e",
    description:
      "CRM coach : coachés, sessions, objectifs et suivi des parcours de transformation.",
    services: ["Coachés", "Sessions", "Objectifs", "Suivi", "Facturation"],
    sector: "CRM / coach",
  },
  {
    id: "planning-rdv",
    label: "Planning & RDV",
    emoji: "📅",
    kinds: ["app_web"],
    project_type: "application_web",
    couleur_primaire: "#059669",
    couleur_secondaire: "#064e3b",
    description:
      "Application de planning : agenda partagé, créneaux et notifications pour équipes terrain.",
    services: ["Agenda", "Créneaux", "Rappels SMS", "Équipes", "Synchronisation"],
    sector: "planning / rendez-vous",
  },
  {
    id: "gestion-entreprise",
    label: "Gestion d'entreprise",
    emoji: "🏢",
    kinds: ["app_web"],
    project_type: "application_web",
    couleur_primaire: "#334155",
    couleur_secondaire: "#0f172a",
    description:
      "Suite de gestion PME : facturation, projets et suivi administratif centralisé.",
    services: ["Facturation", "Projets", "Notes de frais", "Documents", "Utilisateurs"],
    sector: "gestion d'entreprise",
  },
  {
    id: "stock-inventaire",
    label: "Stock & Inventaire",
    emoji: "📦",
    kinds: ["app_web"],
    project_type: "application_web",
    couleur_primaire: "#d97706",
    couleur_secondaire: "#78350f",
    description:
      "Gestion de stocks : inventaires, alertes de rupture et traçabilité multi-dépôts.",
    services: ["Inventaire", "Entrées / sorties", "Alertes stock", "Codes-barres", "Rapports"],
    sector: "stock / inventaire",
  },
  // —— Extension ——
  {
    id: "ecommerce-helper",
    label: "E-commerce helper",
    emoji: "🛒",
    kinds: ["extension"],
    project_type: "extension_navigateur",
    couleur_primaire: "#7c3aed",
    couleur_secondaire: "#2e1065",
    description:
      "Extension navigateur pour e-commerçants : analyse concurrents, prix et optimisation fiches produit.",
    services: ["Veille prix", "SEO produit", "Import catalogue", "Alertes promo", "Raccourcis"],
    sector: "e-commerce / extension",
  },
  {
    id: "productivite",
    label: "Productivité",
    emoji: "📝",
    kinds: ["extension"],
    project_type: "extension_navigateur",
    couleur_primaire: "#0ea5e9",
    couleur_secondaire: "#0c4a6e",
    description:
      "Extension productivité : prise de notes contextuelle, rappels et organisation des onglets.",
    services: ["Notes rapides", "Rappels", "Groupes d'onglets", "Mode focus", "Export"],
    sector: "productivité",
  },
  {
    id: "seo-analytics",
    label: "SEO & Analytics",
    emoji: "🔍",
    kinds: ["extension"],
    project_type: "extension_navigateur",
    couleur_primaire: "#16a34a",
    couleur_secondaire: "#14532d",
    description:
      "Extension SEO : audit instantané des pages, métriques et recommandations d'optimisation.",
    services: ["Audit on-page", "Mots-clés", "Liens", "Core Web Vitals", "Rapport PDF"],
    sector: "SEO / analytics",
  },
  // —— App desktop ——
  {
    id: "artisan-pme",
    label: "Artisan & PME",
    emoji: "🔧",
    kinds: ["desktop"],
    project_type: "application_desktop",
    couleur_primaire: "#b45309",
    couleur_secondaire: "#292524",
    description:
      "Logiciel desktop pour artisans : devis, factures PDF et suivi de chantiers hors-ligne.",
    services: ["Devis", "Factures", "Clients", "Chantiers", "Export comptable"],
    sector: "artisan / PME",
  },
  {
    id: "cabinet-medical",
    label: "Cabinet médical",
    emoji: "🏥",
    kinds: ["desktop"],
    project_type: "application_desktop",
    couleur_primaire: "#0d9488",
    couleur_secondaire: "#134e4a",
    description:
      "Application cabinet médical : dossiers patients, agenda et comptabilité locale sécurisée.",
    services: ["Patients", "Agenda", "Ordonnances", "Comptabilité", "Sauvegarde locale"],
    sector: "cabinet médical",
  },
  {
    id: "ecole-formation",
    label: "École & Formation",
    emoji: "📚",
    kinds: ["desktop"],
    project_type: "application_desktop",
    couleur_primaire: "#4f46e5",
    couleur_secondaire: "#312e81",
    description:
      "Logiciel école / centre de formation : élèves, sessions, présences et bulletins.",
    services: ["Élèves", "Sessions", "Présences", "Notes", "Documents"],
    sector: "école / formation",
  },
  {
    id: "commerce-local",
    label: "Commerce local",
    emoji: "🏪",
    kinds: ["desktop"],
    project_type: "application_desktop",
    couleur_primaire: "#dc2626",
    couleur_secondaire: "#1f2937",
    description:
      "Caisse et gestion commerce local : ventes, stocks et fidélité client en point de vente.",
    services: ["Caisse", "Stock", "Fidélité", "Tickets", "Statistiques jour"],
    sector: "commerce local",
  },
];

export const SECTOR_PRESETS: Record<SectorPresetId, SectorPreset> = Object.fromEntries(
  SECTOR_PRESET_LIST.map((p) => [p.id, p]),
) as Record<SectorPresetId, SectorPreset>;

/** Libellés obligatoires — type Vitrine (étape secteur du générateur). */
export const REQUIRED_VITRINE_SECTOR_LABELS = [
  "Artisan & BTP",
  "Restaurant & Café",
  "Santé & Bien-être",
  "Nautique & Marine",
  "Immobilier & Architecture",
  "Beauté & Coiffure",
  "Formation & Coaching",
  "Garage & Auto",
  "Tourisme & Loisirs",
] as const;

/** Libellés obligatoires — type Réservation (étape secteur du générateur). */
export const REQUIRED_RESERVATION_SECTOR_LABELS = [
  "Camping & Plein air",
  "Hôtel & Hébergement",
  "Gîte & Location saisonnière",
  "Restaurant (réservation table)",
  "Spa & Bien-être",
  "Activités & Loisirs",
  "Location nautique",
] as const;

/** Libellés obligatoires — type E-commerce (étape secteur du générateur). */
export const REQUIRED_ECOMMERCE_SECTOR_LABELS = [
  "Mode & Vêtements",
  "Artisan & Créateur",
  "Bio & Alimentation",
  "High-tech & Électronique",
  "Maison & Déco",
  "Fleurs & Cadeaux",
] as const;

function buildOrderedSectorPresets(
  kind: GeneratorKindId,
  labels: readonly string[],
): SectorPreset[] {
  return labels.map((label) => {
    const preset = SECTOR_PRESET_LIST.find(
      (p) => p.kinds.includes(kind) && p.label === label,
    );
    if (!preset) {
      throw new Error(`Preset ${kind} manquant : ${label}`);
    }
    return preset;
  });
}

/** 9 secteurs vitrine avec couleurs, descriptions et services complets. */
export const VITRINE_SECTOR_PRESETS: SectorPreset[] = buildOrderedSectorPresets(
  "vitrine",
  REQUIRED_VITRINE_SECTOR_LABELS,
);

/** 7 secteurs réservation avec couleurs, descriptions et services complets. */
export const RESERVATION_SECTOR_PRESETS: SectorPreset[] = buildOrderedSectorPresets(
  "reservation",
  REQUIRED_RESERVATION_SECTOR_LABELS,
);

/** 6 secteurs e-commerce avec couleurs, descriptions et services complets. */
export const ECOMMERCE_SECTOR_PRESETS: SectorPreset[] = buildOrderedSectorPresets(
  "ecommerce",
  REQUIRED_ECOMMERCE_SECTOR_LABELS,
);

const SECTORS_BY_KIND: Partial<Record<GeneratorKindId, SectorPreset[]>> = {
  vitrine: VITRINE_SECTOR_PRESETS,
  reservation: RESERVATION_SECTOR_PRESETS,
  ecommerce: ECOMMERCE_SECTOR_PRESETS,
};

export function listSectorsForKind(kind: GeneratorKindId): SectorPreset[] {
  const curated = SECTORS_BY_KIND[kind];
  if (curated) {
    return curated;
  }
  return SECTOR_PRESET_LIST.filter((p) => p.kinds.includes(kind));
}

export function getSectorPreset(id: SectorPresetId | null | undefined): SectorPreset | null {
  if (!id) return null;
  return SECTOR_PRESETS[id] ?? null;
}

/** Associe un libellé/secteur détecté (API clone) à un preset du wizard. */
export function findSectorPresetForHint(
  hint: string,
  kind: GeneratorKindId,
): SectorPreset | null {
  const low = hint.trim().toLowerCase();
  if (!low) return null;
  const options = listSectorsForKind(kind);
  for (const preset of options) {
    if (preset.id.toLowerCase() === low) return preset;
    if (preset.label.toLowerCase() === low) return preset;
    const sectorLow = preset.sector.toLowerCase();
    if (sectorLow.includes(low) || low.includes(sectorLow)) return preset;
    const firstToken = sectorLow.split("/")[0]?.trim() ?? "";
    if (firstToken && (low.includes(firstToken) || firstToken.includes(low))) {
      return preset;
    }
  }
  return null;
}

export function detailsFromPreset(preset: SectorPreset): GeneratorDetailsForm {
  return {
    description: preset.description,
    services: [...preset.services],
    couleur_primaire: preset.couleur_primaire,
    couleur_secondaire: preset.couleur_secondaire,
    ville: "",
    phone: "",
    email: "",
    address: "",
    stripe_publishable_key: "",
  };
}

export function buildGeneratorDetailsPrompt(
  kind: GeneratorKindId,
  form: GeneratorDetailsForm,
  clientName: string,
  sectorLabel: string,
  sectorPreset?: SectorPreset | null,
): string {
  const lines: string[] = [];
  const name = clientName.trim();
  if (name) lines.push(`Client : ${name}`);
  if (sectorLabel.trim()) lines.push(`Secteur : ${sectorLabel.trim()}`);
  if (form.description.trim()) lines.push(form.description.trim());
  if (form.services.length > 0) {
    lines.push(`Services : ${form.services.join(", ")}`);
  }
  if (form.couleur_primaire.trim()) {
    lines.push(`Couleur primaire : ${form.couleur_primaire.trim()}`);
  }
  if (form.couleur_secondaire.trim()) {
    lines.push(`Couleur secondaire : ${form.couleur_secondaire.trim()}`);
  }
  if (form.ville.trim()) lines.push(`Ville : ${form.ville.trim()}`);
  if (form.phone.trim()) lines.push(`Téléphone : ${form.phone.trim()}`);
  if (form.email.trim()) lines.push(`Email : ${form.email.trim()}`);
  if (form.address.trim()) lines.push(`Adresse : ${form.address.trim()}`);
  let prompt = buildGeneratorPipelinePrompt(kind, lines.join("\n"));
  if (sectorPreset?.project_type === "crm") {
    prompt = `TYPE: crm\n${prompt}`;
  }
  return prompt;
}

/** Mappe project_type preset → ProjectType session (approximation). */
export function presetToProjectType(preset: SectorPreset): ProjectType {
  const pt = preset.project_type;
  if (pt === "site_reservation") return "site_web";
  if (pt === "ecommerce") return "saas_dashboard";
  if (pt === "application_web" || pt === "crm") return "application_web";
  if (pt === "application_desktop") return "application_desktop";
  if (pt === "extension_navigateur") return "extension_navigateur";
  return "site_web";
}
