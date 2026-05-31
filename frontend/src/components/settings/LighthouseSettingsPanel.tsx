import { useCallback, useState } from "react";
import {
  isLighthouseEnabled,
  setLighthouseEnabled,
} from "@/lib/lighthouse-preferences";

function LighthouseToggle({
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

/** Toggle audit Lighthouse dans le pipeline. */
export function LighthouseSettingsPanel() {
  const [enabled, setEnabled] = useState(isLighthouseEnabled);
  const refresh = useCallback((next: boolean) => {
    setLighthouseEnabled(next);
    setEnabled(next);
  }, []);

  return (
    <div className="mb-6 rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-cf-text">Lighthouse activé</p>
          <p className="mt-1 text-xs text-cf-muted">
            Audit qualité après Playwright — Performance, SEO, accessibilité et bonnes
            pratiques (score global 0–100).
          </p>
          <p className="mt-2 text-[11px] text-cf-label">
            Score &lt; 70 → recommandations vers AutoFixAI · Score ≥ 70 → export
          </p>
        </div>
        <LighthouseToggle enabled={enabled} onChange={refresh} />
      </div>
    </div>
  );
}
