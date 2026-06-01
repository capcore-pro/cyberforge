import { useCallback, useState } from "react";
import { isStitchEnabled, setStitchEnabled } from "@/lib/stitch-preferences";

function StitchToggle({
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

/** Toggle maquettes StitchAI (Google Stitch) dans le pipeline. */
export function StitchSettingsPanel() {
  const [enabled, setEnabled] = useState(isStitchEnabled);
  const refresh = useCallback((next: boolean) => {
    setStitchEnabled(next);
    setEnabled(next);
  }, []);

  return (
    <div className="mb-6 rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-cf-text">StitchAI activé</p>
          <p className="mt-1 text-xs text-cf-muted">
            Maquettes HTML + captures Google Stitch après ResearchAI — référence
            visuelle pour BuilderAI.
          </p>
          <p className="mt-2 text-[11px] text-cf-label">
            Clé API : section « Clés API Recherche » ci-dessus ou onglet Clés API
          </p>
        </div>
        <StitchToggle enabled={enabled} onChange={refresh} />
      </div>
    </div>
  );
}
