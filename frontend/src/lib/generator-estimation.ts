import type { GeneratorKindId } from "@/lib/generator-kinds";

export type ComplexityTier = "simple" | "medium" | "complex" | "advanced";

export type EstimationProfileId =
  | "vitrine_next"
  | "site_reservation"
  | "ecommerce"
  | "application_web"
  | "application_desktop"
  | "extension_navigateur";

export interface HostingRecommendation {
  providers: string[];
  note: string;
  monthlyEur: number | null;
}

export interface ProjectEstimation {
  profileId: EstimationProfileId;
  complexityTier: ComplexityTier;
  complexityLabel: string;
  apiCostEur: number;
  hosting: HostingRecommendation;
  marketPriceMin: number;
  marketPriceMax: number;
}

const PROFILE_CONFIG: Record<
  EstimationProfileId,
  { tier: ComplexityTier; label: string; apiCostEur: number }
> = {
  vitrine_next: {
    tier: "simple",
    label: "Simple (vitrine)",
    apiCostEur: 0.1,
  },
  site_reservation: {
    tier: "complex",
    label: "Complexe (réservation)",
    apiCostEur: 0.5,
  },
  ecommerce: {
    tier: "complex",
    label: "Complexe (e-commerce)",
    apiCostEur: 0.5,
  },
  application_web: {
    tier: "advanced",
    label: "Avancé (app web)",
    apiCostEur: 0.8,
  },
  application_desktop: {
    tier: "advanced",
    label: "Avancé (app desktop)",
    apiCostEur: 0.8,
  },
  extension_navigateur: {
    tier: "medium",
    label: "Moyen (extension)",
    apiCostEur: 0.3,
  },
};

const TYPE_PREFIX_PROFILE: Record<string, EstimationProfileId> = {
  site_reservation: "site_reservation",
  ecommerce: "ecommerce",
  extension_navigateur: "extension_navigateur",
  application_web: "application_web",
  application_desktop: "application_desktop",
  vitrine_next: "vitrine_next",
};

function kindToProfile(kind: GeneratorKindId): EstimationProfileId {
  switch (kind) {
    case "vitrine":
      return "vitrine_next";
    case "reservation":
      return "site_reservation";
    case "ecommerce":
      return "ecommerce";
    case "app_web":
      return "application_web";
    case "desktop":
      return "application_desktop";
    case "extension":
      return "extension_navigateur";
    default:
      return "vitrine_next";
  }
}

/** Détecte `TYPE: …` en tête de prompt (pipeline GeneratorAI). */
export function profileFromPrompt(prompt: string): EstimationProfileId | null {
  const match = prompt.trim().match(/^TYPE:\s*([^\s\n]+)/im);
  if (!match) return null;
  const key = match[1].toLowerCase().replace(/-/g, "_");
  return TYPE_PREFIX_PROFILE[key] ?? null;
}

export function resolveEstimationProfile(
  kind: GeneratorKindId,
  prompt: string,
): EstimationProfileId {
  return profileFromPrompt(prompt) ?? kindToProfile(kind);
}

/** @deprecated Préférer resolveEstimationProfile — conservé pour compatibilité. */
export function detectComplexityTier(
  kind: GeneratorKindId,
  prompt: string,
): ComplexityTier {
  const profile = resolveEstimationProfile(kind, prompt);
  return PROFILE_CONFIG[profile].tier;
}

export function complexityLabelForProfile(profileId: EstimationProfileId): string {
  return PROFILE_CONFIG[profileId].label;
}

export function apiCostForProfile(profileId: EstimationProfileId): number {
  return PROFILE_CONFIG[profileId].apiCostEur;
}

export function getHostingRecommendation(kind: GeneratorKindId): HostingRecommendation {
  switch (kind) {
    case "vitrine":
    case "reservation":
      return {
        providers: ["Vercel"],
        note: "Vercel (gratuit) recommandé pour les sites vitrine Next.js",
        monthlyEur: 0,
      };
    case "app_web":
      return {
        providers: ["Railway"],
        note: "Railway (~5 €/mois) nécessaire pour une app avec backend",
        monthlyEur: 5,
      };
    case "ecommerce":
      return {
        providers: ["Railway", "Vercel"],
        note: "Railway + Vercel (~5 €/mois) pour boutique et front",
        monthlyEur: 5,
      };
    case "extension":
      return {
        providers: [],
        note: "Pas d'hébergement cloud — publication Chrome Web Store",
        monthlyEur: null,
      };
    case "desktop":
      return {
        providers: [],
        note: "Pas d'hébergement — distribution locale (.exe)",
        monthlyEur: null,
      };
    default:
      return {
        providers: ["Vercel"],
        note: "Vercel (gratuit) recommandé",
        monthlyEur: 0,
      };
  }
}

const MARKET_RANGES: Record<GeneratorKindId, [number, number]> = {
  vitrine: [800, 2500],
  reservation: [1200, 3500],
  app_web: [3000, 12000],
  ecommerce: [5000, 18000],
  extension: [1500, 6000],
  desktop: [4000, 15000],
};

export function computeProjectEstimation(
  kind: GeneratorKindId,
  prompt: string,
): ProjectEstimation {
  const profileId = resolveEstimationProfile(kind, prompt);
  const { tier, label, apiCostEur } = PROFILE_CONFIG[profileId];
  const [marketPriceMin, marketPriceMax] = MARKET_RANGES[kind];
  return {
    profileId,
    complexityTier: tier,
    complexityLabel: label,
    apiCostEur,
    hosting: getHostingRecommendation(kind),
    marketPriceMin,
    marketPriceMax,
  };
}

export function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: value < 1 ? 2 : 0,
    maximumFractionDigits: value < 1 ? 2 : 0,
  }).format(value);
}
