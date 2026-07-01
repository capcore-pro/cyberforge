import type { GeneratorKindId } from "@/lib/generator-kinds";

export type StudioProjectKind = GeneratorKindId | "video";

export type StudioStep = "type" | "sector" | "build";

export type StudioSectionType =
  | "hero"
  | "services"
  | "about"
  | "realisations"
  | "temoignages"
  | "faq"
  | "contact"
  | "catalogue"
  | "panier"
  | "checkout"
  | "dashboard_app"
  | "auth"
  | "fonctionnalites"
  | "interface_desktop"
  | "licence"
  | "scene_video"
  | "musique_video";

export interface StudioSection {
  id: string;
  type: StudioSectionType;
  label: string;
  fields: Record<string, string>;
  imageUrl?: string;
  animationClass?: string;
  aiGenerated: boolean;
  order: number;
}

export const SECTION_LABELS: Record<StudioSectionType, string> = {
  hero: "Hero / Accroche",
  services: "Nos Services",
  about: "À propos",
  realisations: "Réalisations",
  temoignages: "Témoignages",
  faq: "FAQ",
  contact: "Contact",
  catalogue: "Catalogue produits",
  panier: "Panier",
  checkout: "Paiement",
  dashboard_app: "Dashboard",
  auth: "Authentification",
  fonctionnalites: "Fonctionnalités",
  interface_desktop: "Interface logiciel",
  licence: "Licences",
  scene_video: "Scène vidéo",
  musique_video: "Ambiance musicale",
};

const COMMON_SECTIONS: StudioSectionType[] = [
  "hero",
  "services",
  "about",
  "realisations",
  "temoignages",
  "faq",
  "contact",
];

const KIND_EXTRA_SECTIONS: Partial<
  Record<StudioProjectKind, StudioSectionType[]>
> = {
  ecommerce: ["catalogue", "panier", "checkout"],
  app_web: ["dashboard_app", "auth", "fonctionnalites"],
  crm: ["dashboard_app", "auth", "fonctionnalites"],
  desktop: ["interface_desktop", "licence"],
};

export function getAvailableSectionTypes(
  kind: StudioProjectKind | null,
): StudioSectionType[] {
  if (!kind) return [];
  if (kind === "video") return ["scene_video", "musique_video"];
  const extras = KIND_EXTRA_SECTIONS[kind] ?? [];
  return [...COMMON_SECTIONS, ...extras];
}

export function defaultFieldsForSection(
  type: StudioSectionType,
): Record<string, string> {
  switch (type) {
    case "hero":
      return {
        titre: "",
        slogan: "",
        cta_label: "",
        cta_url: "",
        image_fond: "",
        bouton_secondaire: "",
      };
    case "services":
      return {
        titre_section: "",
        services: JSON.stringify([
          { nom: "", description: "", prix: "", icone: "" },
        ]),
      };
    case "about":
      return {
        titre: "",
        texte: "",
        valeurs: "",
        photo_equipe: "",
      };
    case "contact":
      return {
        email: "",
        telephone: "",
        adresse: "",
        formulaire_actif: "true",
        google_maps: "false",
      };
    case "catalogue":
      return {
        titre_section: "",
        produits: JSON.stringify([
          {
            nom: "",
            description: "",
            prix: "",
            statut: "Disponible",
          },
        ]),
        devise: "EUR",
      };
    case "faq":
      return {
        titre_section: "",
        faq: JSON.stringify([{ question: "", reponse: "" }]),
      };
    case "temoignages":
      return {
        titre_section: "",
        temoignages: JSON.stringify([
          { nom_client: "", poste: "", texte: "", note: "5" },
        ]),
      };
    case "realisations":
      return {
        titre_section: "",
        texte_placeholder:
          "Nos premières réalisations arrivent bientôt",
        projets: "[]",
      };
    case "panier":
      return {
        texte_bouton: "Voir le panier",
        devise: "EUR",
        message_livraison: "",
        stripe_actif: "false",
      };
    case "checkout":
      return {
        stripe_publishable_key: "",
        message_confirmation: "",
        redirect_url: "",
      };
    case "dashboard_app":
      return { modules: "", description_dashboard: "" };
    case "auth":
      return {
        type_auth: "email",
        texte_login: "",
        roles: "",
      };
    case "fonctionnalites":
      return {
        fonctionnalites: JSON.stringify([
          { icone: "", titre: "", description: "" },
        ]),
      };
    case "interface_desktop":
      return {
        nom_logiciel: "",
        modules_principaux: "",
        menu_principal: "",
      };
    case "licence":
      return {
        type_licence: "cf-one",
        prix_one_shot: "",
        prix_mensuel: "",
        fonctionnalites_incluses: "",
      };
    case "scene_video":
      return {
        description_fr: "",
        duree_secondes: "5",
        style: "cinématique",
        ordre: "1",
      };
    case "musique_video":
      return {
        style_musical: "Corporate",
        bpm: "Moyen",
        ambiance: "",
      };
    default:
      return { titre_section: "", contenu: "" };
  }
}

export function createStudioSection(
  type: StudioSectionType,
  order: number,
): StudioSection {
  return {
    id: crypto.randomUUID(),
    type,
    label: SECTION_LABELS[type],
    fields: defaultFieldsForSection(type),
    aiGenerated: false,
    order,
  };
}
