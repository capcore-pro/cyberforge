import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import type { GeneratorKindId } from "@/lib/generator-kinds";

const GENERATOR = `${API_PREFIX}/generator`;

export type PromptGeneratorKindId = GeneratorKindId;

export interface GenerateCyberforgePromptPayload {
  project_kind: PromptGeneratorKindId;
  idea: string;
}

export interface GenerateCyberforgePromptResult {
  prompt: string;
}

export function generateCyberforgePrompt(body: GenerateCyberforgePromptPayload) {
  return apiRequest<GenerateCyberforgePromptResult>({
    method: "POST",
    path: `${GENERATOR}/generate-prompt`,
    body,
    timeoutMs: 90_000,
  });
}
