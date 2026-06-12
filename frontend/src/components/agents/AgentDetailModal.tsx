import { useCallback, useEffect, useState } from "react";
import {
  GOLD_BTN,
  GHOST_BTN,
  INPUT,
  LABEL,
  TAB_ACTIVE,
  TAB_BASE,
} from "@/components/settings/settings-theme";
import {
  agentCategoryBadgeClass,
  agentCategoryIcon,
  agentCategoryLabel,
  isKeyConfigured,
} from "@/components/agents/agent-ui";
import {
  fetchAgentDetail,
  fetchAgentMetrics,
  PROVIDER_MODELS,
  toggleAgent,
  updateAgentModel,
  type AgentMetrics,
  type AgentRegistryEntry,
} from "@/lib/agents-api";
import type { VaultConfiguredFlags } from "@/lib/secrets-api";

type DetailTab = "overview" | "model" | "capabilities" | "metrics";

interface AgentDetailModalProps {
  agent: AgentRegistryEntry | null;
  open: boolean;
  secretsConfigured?: VaultConfiguredFlags;
  onClose: () => void;
  onUpdated: (agent: AgentRegistryEntry) => void;
}

const TAB_ITEMS: { id: DetailTab; label: string }[] = [
  { id: "overview", label: "Aperçu" },
  { id: "model", label: "Modèle" },
  { id: "capabilities", label: "Capacités" },
  { id: "metrics", label: "Métriques" },
];

export function AgentDetailModal({
  agent,
  open,
  secretsConfigured,
  onClose,
  onUpdated,
}: AgentDetailModalProps) {
  const [tab, setTab] = useState<DetailTab>("overview");
  const [detail, setDetail] = useState<AgentRegistryEntry | null>(agent);
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("");

  useEffect(() => {
    if (!open || !agent) return;
    setTab("overview");
    setDetail(agent);
    setProvider(agent.provider ?? "anthropic");
    setModel(agent.model ?? "");
    setError(null);
    setMetrics(null);
  }, [open, agent]);

  const loadMetrics = useCallback(async (agentId: string) => {
    setMetricsLoading(true);
    try {
      const data = await fetchAgentMetrics(agentId);
      setMetrics(data);
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open || !detail || tab !== "metrics") return;
    void loadMetrics(detail.agent_id);
  }, [open, detail, tab, loadMetrics]);

  if (!open || !detail) return null;

  const iconClass = agentCategoryIcon(detail.category);
  const keyOk = isKeyConfigured(detail.requires_key, secretsConfigured);

  async function handleToggleEnabled() {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await toggleAgent(detail.agent_id, !detail.enabled);
      setDetail(updated);
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveModel() {
    if (!detail || !model.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateAgentModel(
        detail.agent_id,
        model.trim(),
        provider,
      );
      setDetail(updated);
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshDetail() {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      const fresh = await fetchAgentDetail(detail.agent_id);
      setDetail(fresh);
      onUpdated(fresh);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setBusy(false);
    }
  }

  const modelsForProvider = PROVIDER_MODELS[provider] ?? [];

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="agent-detail-title"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-card border border-white/10 bg-[#0f1117]/95 p-6 shadow-[0_24px_64px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <header className="mb-5 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span
              className="flex h-11 w-11 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-xl text-[#d4a843]"
              aria-hidden
            >
              <i className={iconClass} />
            </span>
            <div>
              <h2 id="agent-detail-title" className="text-lg font-semibold text-white">
                {detail.name}
              </h2>
              <span
                className={`mt-1 inline-block rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase ${agentCategoryBadgeClass(detail.category)}`}
              >
                {agentCategoryLabel(detail.category)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-white/50 transition hover:text-white"
            aria-label="Fermer"
          >
            ×
          </button>
        </header>

        <nav className="mb-5 flex flex-wrap gap-1 border-b border-white/10">
          {TAB_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`${TAB_BASE} ${tab === item.id ? TAB_ACTIVE : ""}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {error ? (
          <p className="mb-4 rounded-control border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            {error}
          </p>
        ) : null}

        {tab === "overview" ? (
          <div className="space-y-4 text-sm text-white/70">
            <p>{detail.description}</p>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-white/40">Statut</p>
                <p className="mt-1 font-medium text-white">
                  {detail.enabled ? "Activé dans le registre" : "Désactivé"}
                </p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleToggleEnabled()}
                className={GHOST_BTN}
              >
                {detail.enabled ? "Désactiver" : "Activer"}
              </button>
            </div>
            <p>
              <span className="text-white/40">Pipeline : </span>
              {detail.in_pipeline
                ? "Oui — agent invoqué dans le pipeline de génération"
                : "Non — agent hors pipeline principal"}
            </p>
            {detail.system_prompt_slug ? (
              <p>
                <span className="text-white/40">Prompt système : </span>
                <button
                  type="button"
                  className="text-[#d4a843] underline-offset-2 hover:underline"
                  onClick={() => {
                    window.dispatchEvent(
                      new CustomEvent("cyberforge:open-prompt-library", {
                        detail: { slug: detail.system_prompt_slug },
                      }),
                    );
                  }}
                >
                  {detail.system_prompt_slug}
                </button>
                <span className="text-white/35"> (Prompt Library)</span>
              </p>
            ) : null}
            {detail.requires_key ? (
              <p>
                <span className="text-white/40">Clé API : </span>
                {keyOk ? (
                  <span className="text-teal-300">Configurée</span>
                ) : (
                  <span className="text-amber-300">
                    Requise ({detail.requires_key}) — à configurer dans Paramètres
                  </span>
                )}
              </p>
            ) : null}
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleRefreshDetail()}
              className={GHOST_BTN}
            >
              Actualiser
            </button>
          </div>
        ) : null}

        {tab === "model" ? (
          <div className="space-y-4">
            <p className="text-sm text-white/55">
              Provider actuel :{" "}
              <span className="text-white">{detail.provider ?? "—"}</span>
              {" · "}
              Modèle : <span className="text-white">{detail.model ?? "—"}</span>
            </p>
            <label className="block">
              <span className={LABEL}>Provider</span>
              <select
                value={provider}
                onChange={(e) => {
                  const next = e.target.value;
                  setProvider(next);
                  const models = PROVIDER_MODELS[next] ?? [];
                  if (models.length > 0) setModel(models[0]);
                }}
                className={INPUT}
              >
                {Object.keys(PROVIDER_MODELS).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={LABEL}>Modèle</span>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className={INPUT}
              >
                {modelsForProvider.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs text-white/40">
              Les agents pipeline utilisent le LLM Router — ce modèle est le défaut
              enregistré dans le registre.
            </p>
            <button
              type="button"
              disabled={busy || !model.trim()}
              onClick={() => void handleSaveModel()}
              className={GOLD_BTN}
            >
              Sauvegarder
            </button>
          </div>
        ) : null}

        {tab === "capabilities" ? (
          <div className="space-y-3">
            {detail.capabilities.length === 0 ? (
              <p className="text-sm text-white/50">Aucune capability enregistrée.</p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {detail.capabilities.map((cap) => (
                  <li
                    key={cap}
                    className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-white/70"
                  >
                    {cap}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {tab === "metrics" ? (
          <div className="space-y-3 text-sm">
            {metricsLoading ? (
              <p className="animate-pulse text-white/50">Chargement des métriques…</p>
            ) : metrics && metrics.total_executions > 0 ? (
              <dl className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <dt className="text-xs text-white/40">Exécutions</dt>
                  <dd className="mt-1 text-lg font-semibold text-white">
                    {metrics.total_executions}
                  </dd>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <dt className="text-xs text-white/40">Coût total estimé</dt>
                  <dd className="mt-1 text-lg font-semibold text-[#d4a843]">
                    ${metrics.total_cost.toFixed(4)}
                  </dd>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <dt className="text-xs text-white/40">Durée moyenne</dt>
                  <dd className="mt-1 text-lg font-semibold text-white">
                    {metrics.avg_duration_ms} ms
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-white/50">
                Aucune exécution enregistrée pour cet agent.
              </p>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
