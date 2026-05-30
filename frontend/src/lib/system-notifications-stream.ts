import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import { isElectronApiAvailable } from "@/lib/api-client";
import type { SystemNotification } from "@/lib/system-notifications-api";

export type SystemNotificationStreamEvent =
  | { type: "stream_start" }
  | { type: "keepalive" }
  | { type: "notification"; data: SystemNotification };

function resolveStreamUrl(): string {
  if (import.meta.env.DEV) {
    return `${API_PREFIX}/notifications/stream`;
  }
  const raw =
    import.meta.env.VITE_API_BASE_URL?.trim() ||
    (isElectronApiAvailable() ? DEFAULT_API_BASE_URL : "");
  if (!raw) {
    return `${API_PREFIX}/notifications/stream`;
  }
  return `${normalizeBackendBaseUrl(raw)}${API_PREFIX}/notifications/stream`;
}

function parseSseData(line: string): SystemNotificationStreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) {
    return null;
  }
  const json = trimmed.slice(5).trim();
  if (!json) {
    return null;
  }
  try {
    return JSON.parse(json) as SystemNotificationStreamEvent;
  } catch {
    return null;
  }
}

export interface SystemNotificationStreamHandlers {
  onEvent?: (event: SystemNotificationStreamEvent) => void;
}

/**
 * Connexion SSE GET — notifications système (keepalive 30 s côté serveur).
 */
export async function connectSystemNotificationsStream(
  handlers: SystemNotificationStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(resolveStreamUrl(), {
    method: "GET",
    headers: { Accept: "text/event-stream" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`SSE notifications HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Flux SSE notifications indisponible");
  }

  const decoder = new TextDecoder();
  let buffer = "";

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
        if (event) {
          handlers.onEvent?.(event);
        }
      }
    }
  }
}
