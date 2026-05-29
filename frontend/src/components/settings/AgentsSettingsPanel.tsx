import { useCallback, useState } from "react";
import {
  isAgentEnabled,
  setAgentEnabled,
  type AgentPreferenceId,
} from "@/lib/agent-preferences";

interface AgentUiDef {
  id: AgentPreferenceId;
  name: string;
  description: string;
  model: string;
}

const AGENTS_UI: AgentUiDef[] = [
  {
    id: "architect",
    name: "Planification",
    description: "Analyse votre description et définit la structure du projet.",
    model: "DeepSeek",
  },
  {
    id: "builder",
    name: "Construction",
    description: "Assemble les pages, sections et composants du site ou de l'app.",
    model: "v0 / DeepSeek",
  },
  {
    id: "coremind",
    name: "Contenu",
    description: "Rédige les textes, titres et messages adaptés à votre activité.",
    model: "Claude",
  },
  {
    id: "visionui",
    name: "Design visuel",
    description: "Harmonise couleurs, mise en page et aspect professionnel.",
    model: "Replicate",
  },
  {
    id: "bughunter",
    name: "Contrôle qualité",
    description: "Repère les erreurs évidentes avant la livraison.",
    model: "DeepSeek",
  },
  {
    id: "autofix",
    name: "Corrections",
    description: "Corrige automatiquement les problèmes détectés.",
    model: "DeepSeek",
  },
  {
    id: "testpilot",
    name: "Tests",
    description: "Vérifie que le résultat est cohérent et utilisable.",
    model: "DeepSeek",
  },
  {
    id: "export",
    name: "Mise en ligne",
    description: "Prépare le déploiement et publie votre projet.",
    model: "—",
  },
];

function AgentToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative h-7 w-12 shrink-0 rounded-full border transition ${
        enabled
          ? "border-cf-gold bg-cf-gold"
          : "border-cf-border-input bg-cf-tertiary/40"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-cf-main transition ${
          enabled ? "left-[22px]" : "left-0.5"
        }`}
      />
    </button>
  );
}

/** Préférences locales des 8 modules de génération. */
export function AgentsSettingsPanel() {
  const [, setTick] = useState(0);
  const refresh = useCallback(() => setTick((n) => n + 1), []);

  return (
    <ul className="space-y-3">
      {AGENTS_UI.map((agent) => {
        const enabled = isAgentEnabled(agent.id);
        return (
          <li
            key={agent.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-4"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-cf-text">{agent.name}</p>
              <p className="mt-1 text-xs text-cf-muted">{agent.description}</p>
              <p className="mt-2 text-[11px] text-cf-label">
                Modèle par défaut :{" "}
                <span className="text-cf-gold">{agent.model}</span>
              </p>
            </div>
            <AgentToggle
              enabled={enabled}
              onChange={(next) => {
                setAgentEnabled(agent.id, next);
                refresh();
              }}
            />
          </li>
        );
      })}
    </ul>
  );
}
