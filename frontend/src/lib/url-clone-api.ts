import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface UrlClonePreviewPayload {
  url: string;
  improved_prompt?: string | null;
}

export interface UrlClonePreviewResponse {
  url: string;
  vertical: string;
  title: string;
  html: string;
  extracted_chars: number;
  notes: string[];
}

export async function previewUrlClone(body: UrlClonePreviewPayload) {
  return apiRequest<UrlClonePreviewResponse>({
    method: "POST",
    path: `${API_PREFIX}/demos/url-clone/preview`,
    body,
  });
}

