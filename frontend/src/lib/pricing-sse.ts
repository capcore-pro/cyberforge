import type { ArchitectPlanCosts, PipelineStepEvent } from "@shared/types";

/** Extrait le plan tarifaire ArchitectAI d'un événement SSE step_done. */
export function architectPlanFromPipelineEvent(
  event: PipelineStepEvent,
): ArchitectPlanCosts | null {
  if (event.type !== "step_done" || event.agent !== "architect") {
    return null;
  }
  const score = event.complexity_score;
  const label = event.complexity_label;
  if (typeof score !== "number" || typeof label !== "string") {
    return null;
  }
  const marketMin = event.market_price_min;
  const marketMax = event.market_price_max;
  const suggestedMin = event.suggested_price_min;
  const suggestedMax = event.suggested_price_max;
  if (
    typeof marketMin !== "number" ||
    typeof marketMax !== "number" ||
    typeof suggestedMin !== "number" ||
    typeof suggestedMax !== "number"
  ) {
    return null;
  }
  return {
    complexity_score: score,
    complexity_label: label,
    market_price_min: marketMin,
    market_price_max: marketMax,
    suggested_price_min: suggestedMin,
    suggested_price_max: suggestedMax,
  };
}
