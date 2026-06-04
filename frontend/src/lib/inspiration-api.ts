import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface ScrapeInspirationResult {
  title: string | null;
  description: string | null;
  primary_color: string | null;
  screenshot_url: string | null;
}

export interface InspirationSectionOut {
  type: string;
  heading: string | null;
  summary: string | null;
}

export interface CloneInspirationResult {
  url: string;
  title: string | null;
  company_name: string;
  client_name: string;
  secteur: string;
  sector_label: string | null;
  project_type: string;
  description: string;
  services: string[];
  couleur_primaire: string;
  couleur_secondaire: string;
  ville: string;
  phone: string;
  email: string;
  address: string;
  brief_builder: string;
  palette: Record<string, string>;
  sections: InspirationSectionOut[];
  screenshot_url: string | null;
}

export function scrapeInspiration(body: { url: string }) {
  return apiRequest<ScrapeInspirationResult>({
    method: "POST",
    path: `${API_PREFIX}/scrape-inspiration`,
    body,
  });
}

export function cloneInspiration(body: {
  url: string;
  project_type: string;
  client_name: string;
}) {
  return apiRequest<CloneInspirationResult>({
    method: "POST",
    path: `${API_PREFIX}/clone-inspiration`,
    body,
  });
}
