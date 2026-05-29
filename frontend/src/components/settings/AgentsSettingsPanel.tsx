import { useCallback, useEffect, useState } from "react";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import {
  isAgentEnabled,
  setAgentEnabled,
  enabledAgentCount,
} from "@/lib/agent-preferences";

/**
 * Activation locale des agents (préférences UI — le pipeline LangGraph reste complet côté serveur).
 */
export function AgentsSettingsPanel() {
  const { status } = useAgentsStatus();
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    void tick;
  }, [tick]);

  const agents = status?.agents ?? [];
  const enabledLocal = enabledAgentCount();
  const total = agents.length || 8;

  return (
    <section className="cyber-panel space-y-4 p-5">
      <div>
        <h2 className="text-sm font-semibold text-cyber-text">Agents IA</h2>
        <p className="mt-1 text-xs text-cyber-muted">
          {enabledLocal} / {total} activés dans l&apos;interface. Ces préférences
          sont enregistrées sur cette machine ; le pipeline serveur exécute encore
          l&apos;ensemble des agents LangGraph tant qu&apos;aucune exclusion backend
          n&apos;est configurée.
        </p>
      </div>
      <ul className="space-y-2">
        {agents.map((agent) => {
          const enabled = isAgentEnabled(agent.id);
          return (
            <li
              key={agent.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-cyber-border bg-cyber-bg/50 px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium text-cyber-text">{agent.name}</p>
                <p className="text-xs text-cyber-muted">{agent.description}</p>
                <p className="mt-0.5 text-[10px] uppercase tracking-wider text-cyber-violet">
                  {agent.in_pipeline ? "Pipeline LangGraph" : "Hors pipeline"}
                  {" · "}
                  {agent.status === "active" ? "Serveur : actif" : "Serveur : veille"}
                </p>
              </div>
              <button
                type="button"
                className={`cyber-action-btn shrink-0 text-[10px] ${
                  enabled ? "border-cyber-neon/50 text-cyber-neon" : ""
                }`}
                onClick={() => {
                  setAgentEnabled(agent.id, !enabled);
                  refresh();
                }}
                aria-pressed={enabled}
              >
                {enabled ? "Activé" : "Désactivé"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
