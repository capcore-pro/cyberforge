import { useCallback, useState } from "react";
import {
  isOpenHandsEnabled,
  setOpenHandsEnabled,
} from "@/lib/openhands-preferences";

function OpenHandsToggle({
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

/** Préférence OpenHands — agent de code avancé pour projets complexes. */
export function OpenHandsSettingsPanel() {
  const [enabled, setEnabled] = useState(isOpenHandsEnabled);
  const refresh = useCallback((next: boolean) => {
    setOpenHandsEnabled(next);
    setEnabled(next);
  }, []);

  return (
    <div className="mb-6 rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-cf-text">OpenHands</p>
          <p className="mt-1 text-xs text-cf-muted">
            Agent de génération de code avancé pour les projets complexes (score
            ≥ 7/10) en mode vraie app ou application web.
          </p>
          <p className="mt-2 text-[11px] text-cf-label">
            Utilise votre clé Anthropic existante — aucune clé supplémentaire
          </p>
        </div>
        <OpenHandsToggle enabled={enabled} onChange={refresh} />
      </div>
    </div>
  );
}
