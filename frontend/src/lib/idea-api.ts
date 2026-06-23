import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

export const IDEA_SECTORS = [
  "Artisanat & BTP",
  "Restauration & Food",
  "Beauté & Bien-être",
  "Santé & Medical",
  "Immobilier",
  "E-commerce & Retail",
  "Sport & Fitness",
  "Education & Formation",
  "Finance & Comptabilité",
  "Transport & Logistique",
  "Tourisme & Hôtellerie",
  "Tech & SaaS",
  "Marketing & Communication",
  "Juridique & Conseil",
  "Agriculture & Nature",
  "Mode & Lifestyle",
  "Musique & Arts",
  "Associations & ONG",
] as const;

export type IdeaMode = "marketing" | "product";

export interface MarketingIdea {
  title: string;
  concept: string;
  emotional_angle: string;
  format: string;
  hook: string;
  video_ready: boolean;
  video_prompt?: string;
}

export interface ProductIdea {
  name: string;
  concept: string;
  problem_solved: string;
  type: string;
  revenue_model: string;
  revenue_potential: string;
  complexity: string;
  dev_time: string;
  cyberforge_ready: boolean;
  cyberforge_type: string;
}

export interface MarketingIdeaResult {
  ideas: MarketingIdea[];
  best_pick?: number;
  summary?: string;
  mode?: string;
  model?: string;
  error?: string;
}

export interface ProductIdeaResult {
  ideas: ProductIdea[];
  best_pick?: number;
  market_insight?: string;
  mode?: string;
  model?: string;
  error?: string;
}

export interface MarketingIdeaRequest {
  sector: string;
  target: string;
  context?: string;
  count?: number;
}

export interface ProductIdeaRequest {
  sector: string;
  target: string;
  budget?: string;
  context?: string;
  count?: number;
}

export async function generateMarketingIdeas(
  body: MarketingIdeaRequest,
): Promise<MarketingIdeaResult> {
  const res = await apiRequest<MarketingIdeaResult>({
    method: "POST",
    path: `${API_PREFIX}/idea/marketing`,
    body,
    timeoutMs: 120_000,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Génération des idées marketing impossible."));
  }
  return res.data ?? { ideas: [] };
}

export async function generateProductIdeas(
  body: ProductIdeaRequest,
): Promise<ProductIdeaResult> {
  const res = await apiRequest<ProductIdeaResult>({
    method: "POST",
    path: `${API_PREFIX}/idea/product`,
    body,
    timeoutMs: 120_000,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Génération des idées produits impossible."));
  }
  return res.data ?? { ideas: [] };
}
