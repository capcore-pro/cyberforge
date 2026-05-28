import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface UnsplashSearchItem {
  id: string;
  url: string;
  thumbUrl?: string | null;
  alt: string;
  photographer?: string | null;
  photographerUrl?: string | null;
  imageQuery?: string | null;
}

export async function searchVitrineImages(
  projectId: string,
  q: string,
  orientation?: string,
  page?: number,
) {
  const params = new URLSearchParams();
  params.set("q", q);
  if (orientation) params.set("orientation", orientation);
  if (page) params.set("page", String(page));
  return apiRequest<UnsplashSearchItem[]>({
    method: "GET",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/images/search?${params.toString()}`,
  });
}

export type VitrineImageSlot = "hero" | "servicesPreview" | "servicesSection";

export async function setVitrineImage(
  projectId: string,
  body: {
    slot: VitrineImageSlot;
    index?: number;
    url: string;
    alt: string;
    photographer?: string | null;
    photographerUrl?: string | null;
    imageQuery?: string | null;
  },
) {
  return apiRequest<{ scheduled: boolean; run_id: string }>({
    method: "POST",
    path: `${API_PREFIX}/managed-projects/vitrines/${projectId}/images/set`,
    body,
    timeoutMs: 120_000,
  });
}

