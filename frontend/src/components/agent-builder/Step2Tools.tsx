import { useEffect, useState } from "react";
import type { CustomAgentUpsert } from "@/lib/custom-agents-api";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";
import { API_PREFIX } from "@shared/constants";

type ToolRow = {
  tool_id: string;
  name: string;
  description: string;
  category: string;
  is_available?: boolean;
};

const BASE_TOOL_IDS = new Set([
  "web_search",
  "http_request",
  "read_file",
  "write_file",
  "execute_code",
  "send_email",
]);

function normalizeTools(items: unknown): ToolRow[] {
  if (!Array.isArray(items)) return [];
  return items.map((row) => {
    const r = row as Record<string, unknown>;
    return {
      tool_id: String(r.tool_id ?? ""),
      name: String(r.name ?? ""),
      description: String(r.description ?? ""),
      category: String(r.category ?? ""),
      is_available: Boolean(r.is_available),
    };
  });
}

export function Step2Tools({
  value,
  disabled,
  onChange,
}: {
  value: CustomAgentUpsert;
  disabled: boolean;
  onChange: (next: CustomAgentUpsert) => void;
}) {
  const [tools, setTools] = useState<ToolRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void apiRequest<{ items?: unknown[] }>({
      method: "GET",
      path: `${API_PREFIX}/tools`,
    })
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          setError(apiErrorMessage(res, "Chargement outils impossible."));
          setTools([]);
          return;
        }
        const all = normalizeTools(res.data?.items ?? []);
        const filtered = all.filter((t) => BASE_TOOL_IDS.has(t.tool_id));
        setTools(filtered.length > 0 ? filtered : all);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Chargement impossible.");
          setTools([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function toggle(toolId: string) {
    const set = new Set(value.tools);
    if (set.has(toolId)) set.delete(toolId);
    else set.add(toolId);
    onChange({ ...value, tools: Array.from(set) });
  }

  return (
    <section>
      <p className="mb-3 text-sm text-cf-muted">
        Sélectionnez les outils disponibles pour cet agent.
      </p>

      {loading ? <p className="text-sm text-cf-muted">Chargement…</p> : null}
      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map((t) => {
          const active = value.tools.includes(t.tool_id);
          return (
            <button
              key={t.tool_id}
              type="button"
              disabled={disabled}
              onClick={() => toggle(t.tool_id)}
              className={[
                "rounded-card border p-4 text-left transition",
                active
                  ? "border-cf-gold/40 bg-cf-gold/10"
                  : "border-white/10 bg-white/5 hover:border-white/20",
                disabled ? "opacity-60" : "",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-cf-text">
                    {t.name}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs text-cf-muted">
                    {t.description || "—"}
                  </p>
                </div>
                <span
                  className={[
                    "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                    active
                      ? "border-cf-gold/40 bg-cf-gold/15 text-cf-gold"
                      : "border-white/10 bg-white/5 text-cf-muted",
                  ].join(" ")}
                >
                  {active ? "ON" : "OFF"}
                </span>
              </div>
              {t.is_available === false ? (
                <p className="mt-2 text-[11px] text-orange-200">
                  Outil indisponible (clé manquante ou service offline).
                </p>
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}

