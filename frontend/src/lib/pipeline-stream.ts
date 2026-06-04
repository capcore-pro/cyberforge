import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import type {
  CoreMindRequest,
  CoreMindRunResponse,
  PipelineStepEvent,
  ProjectType,
} from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import { isElectronApiAvailable } from "@/lib/api-client";
import type { ApiResponsePayload } from "@shared/ipc";

const GENERATE_TIMEOUT_MS = 600_000;

interface GenerateApiResponse {
  url: string;
  html: string;
  success: boolean;
  error?: string | null;
  unlock_url?: string | null;
  demo_token?: string | null;
  demo_password?: string | null;
}

function resolveGenerateUrl(): string {
  if (import.meta.env.DEV) {
    return `${API_PREFIX}/generate`;
  }
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() ||
    (isElectronApiAvailable() ? DEFAULT_API_BASE_URL : "");
  if (!raw) {
    return `${API_PREFIX}/generate`;
  }
  return `${normalizeBackendBaseUrl(raw)}${API_PREFIX}/generate`;
}

function resolveApiProjectType(body: CoreMindRequest): string {
  if (body.generation_mode === "vitrine_next") {
    return "vitrine_next";
  }
  const prompt = (body.prompt || "").trim();
  if (/^TYPE:\s*site_reservation/im.test(prompt)) {
    return "site_reservation";
  }
  if (/^TYPE:\s*ecommerce/im.test(prompt)) {
    return "ecommerce";
  }
  if (/^TYPE:\s*extension_navigateur/im.test(prompt)) {
    return "extension_navigateur";
  }
  const pt = (body.project_type || "site_web") as ProjectType;
  if (pt === "site_web" && body.generation_mode === "client_demo") {
    return "vitrine_next";
  }
  if (pt === "saas_dashboard") {
    return "ecommerce";
  }
  return pt;
}

function resolveClientName(body: CoreMindRequest): string {
  return (
    body.project_title?.trim() ||
    body.pages_project_slug?.trim() ||
    ""
  );
}

function mapGenerateToRunResponse(
  body: CoreMindRequest,
  api: GenerateApiResponse,
): CoreMindRunResponse {
  const html = (api.html || "").trim();
  const projectType = (body.project_type || "site_web") as ProjectType;

  return {
    analysis: {
      agent_id: "cyberforge",
      agent_name: "CyberForge",
      project_type: projectType,
      project_type_label: projectType,
      recommended_tool: "v0",
      tool_rationale: "",
      complexity: "moyenne",
      complexity_score: 5,
      next_steps: [],
      summary: api.success ? "Site généré (pipeline v2)." : (api.error || "Échec génération"),
    },
    generation: {
      code: html,
      files: html ? [{ path: "index.html", content: html }] : [],
      stack: ["html", "css"],
      summary: "",
      model: "cyberforge-v2",
      provider: "cyberforge",
      demo_seed: null,
    },
    metrics: {
      model: "cyberforge-v2",
      provider: "cyberforge",
      complexity: "moyenne",
      complexity_score: 5,
      duration_ms: 0,
      estimated_cost_usd: 0,
      project_type_selected: resolveApiProjectType(body),
    },
    planned_models: ["brief-ai", "generator-ai", "deploy-ai"],
    preview_html: html || null,
    production_url: api.url?.trim() || null,
    export_provider: api.url ? "cloudflare" : null,
    unlock_url: api.unlock_url?.trim() || null,
    demo_token: api.demo_token ?? null,
    demo_password: api.demo_password ?? null,
  };
}

function emitV2Progress(
  handlers: PipelineStreamHandlers,
  phase: "start" | "done",
  agent: PipelineStepEvent["agent"],
  message: string,
  extra?: Partial<PipelineStepEvent>,
) {
  if (!agent) return;
  handlers.onStep?.({
    type: phase === "start" ? "step_start" : "step_done",
    agent,
    message,
    ok: true,
    ...extra,
  });
}

export interface PipelineStreamHandlers {
  onStep?: (event: PipelineStepEvent) => void;
}

/**
 * Lance le pipeline CyberForge v2 via POST /api/generate.
 */
export async function streamCoremindRun(
  body: CoreMindRequest,
  handlers: PipelineStreamHandlers = {},
): Promise<ApiResponsePayload<CoreMindRunResponse>> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), GENERATE_TIMEOUT_MS);

  const emit = (event: PipelineStepEvent) => handlers.onStep?.(event);

  try {
    emit({ type: "pipeline_start" });
    emitV2Progress(handlers, "start", "architect", "Brief client…");
    emitV2Progress(handlers, "start", "builder", "Génération HTML…");

    const response = await fetch(resolveGenerateUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        prompt: body.prompt,
        project_type: resolveApiProjectType(body),
        client_name: resolveClientName(body),
        generation_mode: body.generation_mode ?? null,
        inspiration_brief: body.inspiration_brief ?? null,
        firecrawl_result: body.firecrawl_result ?? null,
      }),
      signal: controller.signal,
    });

    let payload: GenerateApiResponse | null = null;
    try {
      payload = (await response.json()) as GenerateApiResponse;
    } catch {
      payload = null;
    }

    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "error" in payload && payload.error
          ? String(payload.error)
          : response.statusText;
      emit({ type: "pipeline_end", ok: false, message: detail });
      return {
        ok: false,
        status: response.status,
        statusText: detail,
        data: null as CoreMindRunResponse,
      };
    }

    if (!payload?.success || !payload.html?.trim()) {
      const detail = payload?.error?.trim() || "Génération sans HTML valide.";
      emit({ type: "pipeline_end", ok: false, message: detail });
      return {
        ok: false,
        status: 422,
        statusText: detail,
        data: null as CoreMindRunResponse,
      };
    }

    emitV2Progress(handlers, "done", "architect", "Brief validé");
    emitV2Progress(handlers, "done", "builder", "HTML généré", {
      preview_html: payload.html,
    });
    emitV2Progress(handlers, "start", "export", "Déploiement…");
    emitV2Progress(handlers, "done", "export", "Site en ligne", {
      production_url: payload.url,
      unlock_url: payload.unlock_url ?? null,
      demo_password: payload.demo_password ?? null,
    });
    emit({ type: "pipeline_end", ok: true });

    const data = mapGenerateToRunResponse(body, payload);
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      data,
    };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.name === "AbortError"
          ? `Délai dépassé (${GENERATE_TIMEOUT_MS / 1000}s)`
          : error.message
        : "Erreur réseau vers le pipeline";
    emit({ type: "pipeline_end", ok: false, message });
    return {
      ok: false,
      status: 0,
      statusText: message,
      data: null as CoreMindRunResponse,
    };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/** Message utilisateur à partir d'une réponse pipeline. */
export function pipelineStreamErrorMessage(
  response: ApiResponsePayload<CoreMindRunResponse>,
  fallback: string,
): string {
  return apiErrorMessage(response, fallback);
}
