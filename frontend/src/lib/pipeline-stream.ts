import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import type { CoreMindRequest, CoreMindRunResponse, PipelineStepEvent } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import { isElectronApiAvailable } from "@/lib/api-client";
import type { ApiResponsePayload } from "@shared/ipc";

const STREAM_TIMEOUT_MS = 300_000;

function resolveStreamUrl(): string {
  if (import.meta.env.DEV) {
    return `${API_PREFIX}/agents/coremind/run/stream`;
  }
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() ||
    (isElectronApiAvailable() ? DEFAULT_API_BASE_URL : "");
  if (!raw) {
    return `${API_PREFIX}/agents/coremind/run/stream`;
  }
  return `${normalizeBackendBaseUrl(raw)}${API_PREFIX}/agents/coremind/run/stream`;
}

function parseSseData(line: string): PipelineStepEvent | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) {
    return null;
  }
  const json = trimmed.slice(5).trim();
  if (!json) {
    return null;
  }
  try {
    return JSON.parse(json) as PipelineStepEvent;
  } catch {
    return null;
  }
}

export interface PipelineStreamHandlers {
  onStep?: (event: PipelineStepEvent) => void;
}

/**
 * Lance le pipeline LangGraph via SSE (POST) et retourne le résultat final.
 */
export async function streamCoremindRun(
  body: CoreMindRequest,
  handlers: PipelineStreamHandlers = {},
): Promise<ApiResponsePayload<CoreMindRunResponse>> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

  try {
    const response = await fetch(resolveStreamUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errBody = await response.json();
        if (errBody && typeof errBody === "object" && "detail" in errBody) {
          detail = String((errBody as { detail: unknown }).detail);
        }
      } catch {
        /* corps non JSON */
      }
      return {
        ok: false,
        status: response.status,
        statusText: detail,
        data: null as CoreMindRunResponse,
      };
    }

    const reader = response.body?.getReader();
    if (!reader) {
      return {
        ok: false,
        status: 0,
        statusText: "Flux SSE indisponible (body vide)",
        data: null as CoreMindRunResponse,
      };
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult: CoreMindRunResponse | null = null;
    let streamError: string | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const chunk of parts) {
        for (const line of chunk.split("\n")) {
          const event = parseSseData(line);
          if (!event) {
            continue;
          }
          if (
            event.type === "step_start" ||
            event.type === "step_done" ||
            event.type === "step_error" ||
            event.type === "pipeline_start" ||
            event.type === "pipeline_end"
          ) {
            handlers.onStep?.(event);
          } else if (event.type === "result") {
            const raw = event as PipelineStepEvent & { data?: CoreMindRunResponse };
            if (raw.data) {
              finalResult = raw.data;
            }
          } else if (event.type === "error") {
            streamError =
              "detail" in event
                ? String((event as { detail: unknown }).detail)
                : "Erreur pipeline";
          }
        }
      }
    }

    if (streamError) {
      return {
        ok: false,
        status: 422,
        statusText: streamError,
        data: null as CoreMindRunResponse,
      };
    }

    if (!finalResult) {
      return {
        ok: false,
        status: 0,
        statusText: "Pipeline terminé sans résultat",
        data: null as CoreMindRunResponse,
      };
    }

    return {
      ok: true,
      status: 200,
      statusText: "OK",
      data: finalResult,
    };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.name === "AbortError"
          ? `Délai dépassé (${STREAM_TIMEOUT_MS / 1000}s)`
          : error.message
        : "Erreur réseau vers le pipeline";
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

/** Message utilisateur à partir d'une réponse stream. */
export function pipelineStreamErrorMessage(
  response: ApiResponsePayload<CoreMindRunResponse>,
  fallback: string,
): string {
  return apiErrorMessage(response, fallback);
}
