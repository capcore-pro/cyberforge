import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";
import { buildBackendApiUrl } from "@/lib/backend-url";

export interface CustomAgentRecord {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface CustomAgentUpsert {
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  is_active: boolean;
}

function normalizeAgent(row: Record<string, unknown>): CustomAgentRecord {
  const tools = Array.isArray(row.tools) ? row.tools.map((x) => String(x)) : [];
  return {
    id: String(row.id ?? ""),
    name: String(row.name ?? ""),
    description: row.description != null ? String(row.description) : null,
    system_prompt: String(row.system_prompt ?? ""),
    model: String(row.model ?? ""),
    temperature: Number(row.temperature ?? 0.7),
    max_tokens: Number(row.max_tokens ?? 2048),
    tools,
    is_active: Boolean(row.is_active),
    created_at: row.created_at != null ? String(row.created_at) : null,
    updated_at: row.updated_at != null ? String(row.updated_at) : null,
  };
}

export async function listCustomAgents(): Promise<CustomAgentRecord[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/agents/custom`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Impossible de charger les agents custom."));
  }
  const items = Array.isArray(res.data?.items) ? res.data?.items : [];
  return items.map((row) => normalizeAgent(row as Record<string, unknown>));
}

export async function getCustomAgent(id: string): Promise<CustomAgentRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/agents/custom/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Agent introuvable."));
  }
  return normalizeAgent(res.data ?? {});
}

export async function createCustomAgent(
  payload: CustomAgentUpsert,
): Promise<CustomAgentRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "POST",
    path: `${API_PREFIX}/agents/custom`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Création impossible."));
  }
  return normalizeAgent(res.data ?? {});
}

export async function updateCustomAgent(
  id: string,
  payload: CustomAgentUpsert,
): Promise<CustomAgentRecord> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "PUT",
    path: `${API_PREFIX}/agents/custom/${encodeURIComponent(id)}`,
    body: payload,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Mise à jour impossible."));
  }
  return normalizeAgent(res.data ?? {});
}

export async function deleteCustomAgent(id: string): Promise<void> {
  const res = await apiRequest<{ deleted?: boolean }>({
    method: "DELETE",
    path: `${API_PREFIX}/agents/custom/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Suppression impossible."));
  }
}

export interface CustomAgentChatDone {
  content: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  duration_ms: number;
}

export interface CustomAgentChatHandlers {
  onChunk: (delta: string) => void;
  onDone: (payload: CustomAgentChatDone) => void;
  onError: (message: string) => void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseDonePayload(value: unknown): CustomAgentChatDone | null {
  if (!isRecord(value)) return null;
  return {
    content: String(value.content ?? ""),
    provider: String(value.provider ?? ""),
    model: String(value.model ?? ""),
    input_tokens: Number(value.input_tokens ?? 0),
    output_tokens: Number(value.output_tokens ?? 0),
    total_tokens: Number(value.total_tokens ?? 0),
    cost_usd: Number(value.cost_usd ?? 0),
    duration_ms: Number(value.duration_ms ?? 0),
  };
}

function parseSseBlocks(text: string): Array<{ event?: string; data?: string }> {
  return text
    .split("\n\n")
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split("\n");
      const ev = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
      const data = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
      return { event: ev, data };
    });
}

export async function streamCustomAgentChat(
  agentId: string,
  message: string,
  history: Array<{ role: "user" | "assistant"; content: string }>,
  handlers: CustomAgentChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const path = `${API_PREFIX}/agents/custom/${encodeURIComponent(agentId)}/chat`;
  const url =
    import.meta.env.DEV && typeof window !== "undefined"
      ? path
      : buildBackendApiUrl(path);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!response.ok || !response.body) {
    let detail = `Chat impossible (${response.status})`;
    try {
      const payload = (await response.json()) as unknown;
      detail = apiErrorMessage(
        { status: response.status, statusText: response.statusText, data: payload },
        detail,
      );
    } catch {
      // ignore
    }
    handlers.onError(detail);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      for (const parsed of parseSseBlocks(block)) {
        if (!parsed.event || !parsed.data) continue;
        try {
          const payload = JSON.parse(parsed.data) as unknown;
          if (parsed.event === "chunk") {
            handlers.onChunk(
              isRecord(payload) ? String(payload.delta ?? "") : "",
            );
          } else if (parsed.event === "done") {
            const done = parseDonePayload(payload);
            if (done) handlers.onDone(done);
          } else if (parsed.event === "error") {
            handlers.onError(
              isRecord(payload)
                ? String(payload.message ?? "Erreur inconnue.")
                : "Erreur inconnue.",
            );
          }
        } catch {
          // ignore malformed blocks
        }
      }
    }
  }
}

