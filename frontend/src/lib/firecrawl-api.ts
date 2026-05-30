import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const FIRECRAWL = `${API_PREFIX}/firecrawl`;

export interface ScrapeSectionOut {
  type: string;
  heading: string | null;
  summary: string | null;
}

export interface CloneInspirationPayload {
  url: string;
  secteur: string;
  nom_client: string;
}

export interface CloneInspirationResult {
  url: string;
  secteur: string;
  nom_client: string;
  brief_builder: string;
  palette: Record<string, string>;
  sections: ScrapeSectionOut[];
  placeholders: Record<string, string>;
  images: {
    source_url: string;
    stock_url: string | null;
    stock_source: string | null;
    query: string | null;
  }[];
}

export interface AnalyzeCompetitorPayload {
  url: string;
  secteur: string;
}

export interface AnalyzeCompetitorResult {
  url: string;
  secteur: string;
  analyse: string;
  points_forts: string[];
  points_faibles: string[];
  suggestions: string[];
  composants_recommandes: string[];
}

export function cloneFirecrawlInspiration(body: CloneInspirationPayload) {
  return apiRequest<CloneInspirationResult>({
    method: "POST",
    path: `${FIRECRAWL}/clone-inspiration`,
    body,
  });
}

export function analyzeFirecrawlCompetitor(body: AnalyzeCompetitorPayload) {
  return apiRequest<AnalyzeCompetitorResult>({
    method: "POST",
    path: `${FIRECRAWL}/analyze-competitor`,
    body,
  });
}
