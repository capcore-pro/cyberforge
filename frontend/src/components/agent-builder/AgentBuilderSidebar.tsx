import type { CustomAgentRecord } from "@/lib/custom-agents-api";
import { Button } from "@/components/ui";

function providerBadge(model: string): { label: string; className: string } {
  const key = (model || "").toLowerCase();
  if (key.startsWith("claude-")) {
    return { label: "Anthropic", className: "border-violet-500/40 bg-violet-500/10 text-violet-200" };
  }
  if (key.startsWith("mistral-")) {
    return { label: "Mistral", className: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200" };
  }
  if (key.includes("ollama") || key.startsWith("qwen") || key.startsWith("deepseek")) {
    return { label: "Ollama", className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" };
  }
  return { label: "LLM", className: "border-white/10 bg-white/5 text-cf-muted" };
}

export function AgentBuilderSidebar({
  agents,
  selectedId,
  loading,
  onSelect,
  onNew,
  onDelete,
  onClone,
  onToggleActive,
}: {
  agents: CustomAgentRecord[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClone: (agent: CustomAgentRecord) => void;
  onToggleActive: (id: string, active: boolean) => void;
}) {
  return (
    <aside className="w-[280px] shrink-0 border-r border-white/10 bg-[#0f1117]/60 p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          Agents custom
        </p>
        <Button
          variant="primary"
          size="sm"
          icon="ti ti-plus"
          onClick={onNew}
        >
          Nouvel agent
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-cf-muted">Chargement…</p>
      ) : agents.length === 0 ? (
        <p className="text-sm text-cf-muted">
          Aucun agent. Créez votre premier agent custom.
        </p>
      ) : (
        <div className="space-y-2">
          {agents.map((agent) => {
            const selected = agent.id === selectedId;
            const badge = providerBadge(agent.model);
            return (
              <div
                key={agent.id}
                className={[
                  "rounded-card border p-3",
                  selected
                    ? "border-cf-gold/40 bg-white/7"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <button
                  type="button"
                  onClick={() => onSelect(agent.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-cf-text">
                        {agent.name}
                      </p>
                      <p className="mt-1 line-clamp-2 text-xs text-cf-muted">
                        {agent.description ?? "—"}
                      </p>
                    </div>
                    <span
                      className={[
                        "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                        badge.className,
                      ].join(" ")}
                    >
                      {badge.label}
                    </span>
                  </div>
                </button>

                <div className="mt-3 flex items-center justify-between gap-2">
                  <label className="inline-flex items-center gap-2 text-xs text-cf-muted">
                    <input
                      type="checkbox"
                      checked={agent.is_active}
                      onChange={(e) => onToggleActive(agent.id, e.target.checked)}
                    />
                    Actif
                  </label>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className="rounded-control border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-cf-muted hover:border-white/20 hover:text-cf-text"
                      onClick={() => onClone(agent)}
                    >
                      Clone
                    </button>
                    <button
                      type="button"
                      className="rounded-control border border-red-500/30 bg-red-950/20 px-2 py-1 text-[11px] text-red-200 hover:border-red-500/50"
                      onClick={() => onDelete(agent.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}

