import type { GeneratorKindId } from "@/lib/generator-kinds";

export type ComplexityTier = "simple" | "medium" | "complex";

export interface HostingRecommendation {
  providers: string[];
  note: string;
  monthlyEur: number | null;
}

export interface ProjectEstimation {
  complexityTier: ComplexityTier;
  complexityLabel: string;
  apiCostEur: number;
  hosting: HostingRecommendation;
  marketPriceMin: number;
  marketPriceMax: number;
}

const ECOMMERCE_KEYWORDS = [
  "e-commerce",
  "ecommerce",
  "boutique",
  "panier",
  "checkout",
  "stripe",
  "paiement",
  "catalogue produit",
  "marketplace",
];

const APP_KEYWORDS = [
  "crm",
  "dashboard",
  "tableau de bord",
  "authentification",
  "base de données",
  "api",
  "portail",
  "gestion",
  "stock",
  "back-office",
  "saas",
];

const VITRINE_KEYWORDS = [
  "vitrine",
  "présenter",
  "boulangerie",
  "restaurant",
  "cabinet",
  "portfolio",
  "landing",
  "site web",
  "multi-pages",
];

function kindBaseTier(kind: GeneratorKindId): ComplexityTier {
  switch (kind) {
    case "vitrine":
    case "reservation":
      return "simple";
    case "extension":
    case "desktop":
      return "medium";
    case "app_web":
      return "medium";
    case "ecommerce":
      return "complex";
    default:
      return "simple";
  }
}

function promptTier(prompt: string): ComplexityTier | null {
  const lower = prompt.toLowerCase();
  if (ECOMMERCE_KEYWORDS.some((kw) => lower.includes(kw))) return "complex";
  if (APP_KEYWORDS.some((kw) => lower.includes(kw))) return "medium";
  if (VITRINE_KEYWORDS.some((kw) => lower.includes(kw))) return "simple";
  return null;
}

function maxTier(a: ComplexityTier, b: ComplexityTier): ComplexityTier {
  const order: ComplexityTier[] = ["simple", "medium", "complex"];
  return order[Math.max(order.indexOf(a), order.indexOf(b))];
}

export function detectComplexityTier(
  kind: GeneratorKindId,
  prompt: string,
): ComplexityTier {
  const base = kindBaseTier(kind);
  const fromPrompt = promptTier(prompt.trim());
  if (!fromPrompt) return base;
  return maxTier(base, fromPrompt);
}

export function complexityLabel(tier: ComplexityTier): string {
  switch (tier) {
    case "simple":
      return "Simple (vitrine)";
    case "medium":
      return "Moyen (app web)";
    case "complex":
      return "Complexe (e-commerce)";
  }
}

export function estimateApiCostEur(tier: ComplexityTier): number {
  switch (tier) {
    case "simple":
      return 0.1;
    case "medium":
      return 0.3;
    case "complex":
      return 0.5;
  }
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
  const complexityTier = detectComplexityTier(kind, prompt);
  const [marketPriceMin, marketPriceMax] = MARKET_RANGES[kind];
  return {
    complexityTier,
    complexityLabel: complexityLabel(complexityTier),
    apiCostEur: estimateApiCostEur(complexityTier),
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
