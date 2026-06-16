import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import type {
  CoreMindRequest,
  CoreMindRunResponse,
  PipelineAgentId,
  PipelineStepEvent,
  ProjectType,
} from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import { isElectronApiAvailable } from "@/lib/api-client";
import type { ApiResponsePayload } from "@shared/ipc";

const GENERATE_TIMEOUT_MS = 600_000;

interface GenerateStartResponse {
  generation_id: string;
  status: string;
}

interface GenerateApiResponse {
  url: string;
  html: string;
  success: boolean;
  error?: string | null;
  unlock_url?: string | null;
  demo_token?: string | null;
  demo_password?: string | null;
  duration_ms?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  estimated_cost_usd?: number | null;
}

const AGENT_TO_STEP: Record<string, PipelineAgentId> = {
  BriefAI: "architect",
  GeneratorAI: "builder",
  SupervisorAI: "bughunter",
  ElectronAI: "builder",
  DeployAI: "export",
};

const AGENT_START_MESSAGES: Record<string, string> = {
  BriefAI: "BriefAI — Analyse et enrichissement du brief",
  GeneratorAI: "GeneratorAI — Génération HTML premium",
  SupervisorAI: "SupervisorAI — Validation HTML",
  ElectronAI: "ElectronAI — Package Electron Windows",
  DeployAI: "DeployAI — Images Pexels + Cloudflare",
};

const AGENT_DONE_MESSAGES: Record<string, string> = {
  BriefAI: "Brief enrichi",
  GeneratorAI: "HTML généré",
  SupervisorAI: "Contrôle qualité validé",
  ElectronAI: "Fichiers Electron générés",
  DeployAI: "Démo en ligne",
};

function resolveApiBase(): string {
  if (import.meta.env.DEV) {
    return "";
  }
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() ||
    (isElectronApiAvailable() ? DEFAULT_API_BASE_URL : "");
  if (!raw) {
    return "";
  }
  return normalizeBackendBaseUrl(raw);
}

function resolveGenerateUrl(): string {
  const base = resolveApiBase();
  return base ? `${base}${API_PREFIX}/generate` : `${API_PREFIX}/generate`;
}

function resolveGenerateSyncUrl(): string {
  const base = resolveApiBase();
  return base ? `${base}${API_PREFIX}/generate/sync` : `${API_PREFIX}/generate/sync`;
}

function resolveGenerateStreamUrl(generationId: string): string {
  const base = resolveApiBase();
  const path = `${API_PREFIX}/generate/stream/${encodeURIComponent(generationId)}`;
  return base ? `${base}${path}` : path;
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
  if (/^TYPE:\s*crm/im.test(prompt)) {
    return "crm";
  }
  if (/^TYPE:\s*application_desktop/im.test(prompt)) {
    return "application_desktop";
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

function buildGenerateBody(body: CoreMindRequest) {
  return {
    prompt: body.prompt,
    project_type: resolveApiProjectType(body),
    client_name: resolveClientName(body),
    generation_mode: body.generation_mode ?? null,
    inspiration_brief: body.inspiration_brief ?? null,
    firecrawl_result: body.firecrawl_result ?? null,
    stripe_publishable_key: body.stripe_publishable_key?.trim() || null,
  };
}

function mapGenerateToRunResponse(
  body: CoreMindRequest,
  api: GenerateApiResponse,
): CoreMindRunResponse {
  const html = (api.html || "").trim();
  const projectType = (body.project_type || "site_web") as ProjectType;
  const durationMs = api.duration_ms ?? 0;

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
      duration_ms: durationMs,
      estimated_cost_usd: api.estimated_cost_usd ?? 0,
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

function emitStep(
  handlers: PipelineStreamHandlers,
  phase: "start" | "done",
  agent: PipelineAgentId,
  message: string,
  extra?: Partial<PipelineStepEvent>,
) {
  handlers.onStep?.({
    type: phase === "start" ? "step_start" : "step_done",
    agent,
    message,
    ok: true,
    ...extra,
  });
}

export interface AgentRetryEvent {
  agent: string;
  attempt: number;
  reason: string;
}

export interface PipelineStreamHandlers {
  onStep?: (event: PipelineStepEvent) => void;
  onAgentRetry?: (event: AgentRetryEvent) => void;
  onAgentDuration?: (agent: string, durationMs: number) => void;
  onServerDuration?: (durationMs: number) => void;
}

function parseSseData<T>(raw: string): T {
  return JSON.parse(raw) as T;
}

function waitForGenerationSse(
  generationId: string,
  handlers: PipelineStreamHandlers,
  signal: AbortSignal,
): Promise<GenerateApiResponse> {
  return new Promise((resolve, reject) => {
    const es = new EventSource(resolveGenerateStreamUrl(generationId));
    let settled = false;

    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      es.close();
      fn();
    };

    const onAbort = () => {
      finish(() => {
        reject(new DOMException("Génération annulée", "AbortError"));
      });
    };
    signal.addEventListener("abort", onAbort, { once: true });

    es.addEventListener("agent_start", (event: Event) => {
      const msg = event as MessageEvent<string>;
      const data = parseSseData<{ agent: string; step: number; total: number }>(
        msg.data,
      );
      const stepId = AGENT_TO_STEP[data.agent];
      if (!stepId) return;
      emitStep(
        handlers,
        "start",
        stepId,
        AGENT_START_MESSAGES[data.agent] ??
          `${data.agent} — étape ${data.step}/${data.total}`,
      );
    });

    es.addEventListener("agent_done", (event: Event) => {
      const msg = event as MessageEvent<string>;
      const data = parseSseData<{
        agent: string;
        step: number;
        duration_ms: number;
      }>(msg.data);
      const stepId = AGENT_TO_STEP[data.agent];
      if (!stepId) return;
      handlers.onAgentDuration?.(data.agent, data.duration_ms);
      const extra: Partial<PipelineStepEvent> = {};
      if (data.agent === "GeneratorAI") {
        // preview may arrive on done from server later
      }
      emitStep(
        handlers,
        "done",
        stepId,
        AGENT_DONE_MESSAGES[data.agent] ?? `${data.agent} terminé`,
        extra,
      );
    });

    es.addEventListener("agent_retry", (event: Event) => {
      const msg = event as MessageEvent<string>;
      const data = parseSseData<AgentRetryEvent>(msg.data);
      handlers.onAgentRetry?.(data);
    });

    es.addEventListener("done", (event: Event) => {
      const msg = event as MessageEvent<string>;
      const data = parseSseData<GenerateApiResponse>(msg.data);
      if (typeof data.duration_ms === "number") {
        handlers.onServerDuration?.(data.duration_ms);
      }
      const builderId = AGENT_TO_STEP.GeneratorAI;
      if (builderId && data.html?.trim()) {
        emitStep(handlers, "done", builderId, "HTML premium généré", {
          preview_html: data.html,
        });
      }
      const exportId = AGENT_TO_STEP.DeployAI;
      if (exportId) {
        emitStep(handlers, "done", exportId, "Démo en ligne", {
          production_url: data.url,
          unlock_url: data.unlock_url ?? null,
          demo_password: data.demo_password ?? null,
        });
      }
      signal.removeEventListener("abort", onAbort);
      finish(() => {
        resolve({
          url: data.url ?? "",
          html: data.html ?? "",
          success: true,
          unlock_url: data.unlock_url,
          demo_token: data.demo_token,
          demo_password: data.demo_password,
          duration_ms: data.duration_ms,
          input_tokens: data.input_tokens,
          output_tokens: data.output_tokens,
          total_tokens: data.total_tokens,
          estimated_cost_usd: data.estimated_cost_usd,
        });
      });
    });

    es.addEventListener("error", (event: Event) => {
      if (event instanceof MessageEvent) {
        const data = parseSseData<{ message?: string }>(event.data);
        signal.removeEventListener("abort", onAbort);
        finish(() => {
          reject(new Error(data.message?.trim() || "Erreur pipeline"));
        });
      }
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED && !settled) {
        signal.removeEventListener("abort", onAbort);
        finish(() => {
          reject(new Error("Connexion SSE interrompue"));
        });
      }
    };
  });
}

/**
 * Lance le pipeline CyberForge v2 via POST /api/generate + SSE.
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

    const startResponse = await fetch(resolveGenerateUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(buildGenerateBody(body)),
      signal: controller.signal,
    });

    let startPayload: GenerateStartResponse | GenerateApiResponse | null = null;
    try {
      startPayload = (await startResponse.json()) as
        | GenerateStartResponse
        | GenerateApiResponse;
    } catch {
      startPayload = null;
    }

    if (!startResponse.ok) {
      const detail =
        startPayload && "error" in startPayload && startPayload.error
          ? String(startPayload.error)
          : startResponse.statusText;
      emit({ type: "pipeline_end", ok: false, message: detail });
      return {
        ok: false,
        status: startResponse.status,
        statusText: detail,
        data: null as CoreMindRunResponse,
      };
    }

    const generationId =
      startPayload && "generation_id" in startPayload
        ? startPayload.generation_id
        : null;

    if (!generationId) {
      emit({ type: "pipeline_end", ok: false, message: "generation_id manquant" });
      return {
        ok: false,
        status: 502,
        statusText: "generation_id manquant",
        data: null as CoreMindRunResponse,
      };
    }

    const payload = await waitForGenerationSse(
      generationId,
      handlers,
      controller.signal,
    );

    if (!payload.success || !payload.html?.trim()) {
      const detail = payload.error?.trim() || "Génération sans HTML valide.";
      emit({ type: "pipeline_end", ok: false, message: detail });
      return {
        ok: false,
        status: 422,
        statusText: detail,
        data: null as CoreMindRunResponse,
      };
    }

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

/** Pipeline synchrone — tests et scripts (POST /api/generate/sync). */
export async function streamCoremindRunSync(
  body: CoreMindRequest,
): Promise<ApiResponsePayload<CoreMindRunResponse>> {
  const response = await fetch(resolveGenerateSyncUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(buildGenerateBody(body)),
  });
  const payload = (await response.json()) as GenerateApiResponse;
  if (!response.ok || !payload.success) {
    return {
      ok: false,
      status: response.status,
      statusText: payload.error || response.statusText,
      data: null as CoreMindRunResponse,
    };
  }
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    data: mapGenerateToRunResponse(body, payload),
  };
}

/** Message utilisateur à partir d'une réponse pipeline. */
export function pipelineStreamErrorMessage(
  response: ApiResponsePayload<CoreMindRunResponse>,
  fallback: string,
): string {
  return apiErrorMessage(response, fallback);
}
