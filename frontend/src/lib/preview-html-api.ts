import { API_PREFIX } from "@shared/constants";
import type { DemoSeedPayload } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

export async function fetchTaskflowPreviewHtml(
  demo_seed: DemoSeedPayload,
  options?: { prompt?: string; project_type_label?: string },
): Promise<string | null> {
  const response = await apiRequest<{ html: string }>({
    method: "POST",
    path: `${API_PREFIX}/agents/coremind/preview-html`,
    body: {
      demo_seed,
      prompt: options?.prompt ?? null,
      project_type_label: options?.project_type_label ?? null,
    },
  });
  if (!response.ok || !response.data?.html?.trim()) {
    return null;
  }
  return response.data.html.trim();
}
