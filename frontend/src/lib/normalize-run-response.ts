import type { CoreMindRunResponse } from "@shared/types";

/** Normalise une réponse CoreMind (historique local parfois incomplet). */
export function normalizeRunResponse(
  raw: CoreMindRunResponse | null | undefined,
): CoreMindRunResponse | null {
  if (!raw || typeof raw !== "object") return null;

  const generation = raw.generation;
  if (!generation || typeof generation !== "object") return null;

  const code =
    typeof generation.code === "string" ? generation.code : "";
  const files = Array.isArray(generation.files)
    ? generation.files.filter(
        (f) => f && typeof f.path === "string" && typeof f.content === "string",
      )
    : code
      ? [{ path: "src/App.tsx", content: code }]
      : [];

  const analysis = raw.analysis;
  if (!analysis || typeof analysis !== "object") return null;

  const metrics = raw.metrics;
  if (!metrics || typeof metrics !== "object") return null;

  return {
    ...raw,
    generation: {
      ...generation,
      code,
      files,
      stack: Array.isArray(generation.stack) ? generation.stack : [],
      summary:
        typeof generation.summary === "string" ? generation.summary : "",
      model: typeof generation.model === "string" ? generation.model : "",
      provider:
        typeof generation.provider === "string" ? generation.provider : "",
    },
    planned_models: Array.isArray(raw.planned_models)
      ? raw.planned_models
      : [],
  };
}
