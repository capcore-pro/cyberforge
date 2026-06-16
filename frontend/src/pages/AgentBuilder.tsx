import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createCustomAgent,
  deleteCustomAgent,
  listCustomAgents,
  updateCustomAgent,
  type CustomAgentRecord,
  type CustomAgentUpsert,
} from "@/lib/custom-agents-api";
import { AgentBuilderSidebar } from "@/components/agent-builder/AgentBuilderSidebar";
import { AgentBuilderWizard } from "@/components/agent-builder/AgentBuilderWizard";

const EMPTY_AGENT: CustomAgentUpsert = {
  name: "",
  description: "",
  system_prompt: "",
  model: "claude-sonnet-4-6",
  temperature: 0.7,
  max_tokens: 2048,
  tools: [],
  is_active: true,
};

export function AgentBuilder() {
  const [agents, setAgents] = useState<CustomAgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(
    () => agents.find((a) => a.id === selectedId) ?? null,
    [agents, selectedId],
  );

  const [draft, setDraft] = useState<CustomAgentUpsert>(EMPTY_AGENT);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listCustomAgents();
      setAgents(items);
      if (!selectedId && items[0]?.id) {
        setSelectedId(items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selected) {
      setDraft({
        name: selected.name,
        description: selected.description ?? "",
        system_prompt: selected.system_prompt,
        model: selected.model,
        temperature: selected.temperature,
        max_tokens: selected.max_tokens,
        tools: selected.tools,
        is_active: selected.is_active,
      });
    } else {
      setDraft(EMPTY_AGENT);
    }
  }, [selected?.id]);

  async function handleSave(payload: CustomAgentUpsert) {
    setBusy(true);
    setError(null);
    try {
      const saved = selected
        ? await updateCustomAgent(selected.id, payload)
        : await createCustomAgent(payload);
      setToast(selected ? "✓ Agent mis à jour" : "✓ Agent créé");
      window.setTimeout(() => setToast(null), 4000);
      await load();
      setSelectedId(saved.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sauvegarde impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    setBusy(true);
    setError(null);
    try {
      await deleteCustomAgent(id);
      setToast("Agent supprimé");
      window.setTimeout(() => setToast(null), 4000);
      setSelectedId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function handleClone(agent: CustomAgentRecord) {
    const cloned: CustomAgentUpsert = {
      name: `${agent.name} (clone)`,
      description: agent.description ?? "",
      system_prompt: agent.system_prompt,
      model: agent.model,
      temperature: agent.temperature,
      max_tokens: agent.max_tokens,
      tools: agent.tools,
      is_active: true,
    };
    await handleSave(cloned);
  }

  function handleNewAgent() {
    setSelectedId(null);
    setDraft(EMPTY_AGENT);
  }

  return (
    <div className="flex min-h-[70vh] rounded-card border border-white/10 bg-white/5 backdrop-blur-xl">
      <AgentBuilderSidebar
        agents={agents}
        selectedId={selectedId}
        loading={loading}
        onSelect={setSelectedId}
        onNew={handleNewAgent}
        onDelete={handleDelete}
        onClone={handleClone}
        onToggleActive={async (id, active) => {
          const existing = agents.find((a) => a.id === id);
          if (!existing) return;
          await handleSave({
            name: existing.name,
            description: existing.description ?? "",
            system_prompt: existing.system_prompt,
            model: existing.model,
            temperature: existing.temperature,
            max_tokens: existing.max_tokens,
            tools: existing.tools,
            is_active: active,
          });
        }}
      />

      <div className="flex-1 p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-cf-text">
              Agent Builder
            </h1>
            <p className="text-sm text-cf-muted">
              Créez des agents custom utilisables en chat et dans les workflows.
            </p>
          </div>
          {toast ? (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              {toast}
            </span>
          ) : null}
        </div>

        {error ? (
          <p className="mb-4 rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        <AgentBuilderWizard
          agentId={selected?.id ?? null}
          value={draft}
          disabled={busy}
          onChange={setDraft}
          onSave={handleSave}
        />
      </div>
    </div>
  );
}

