import type { MobileAppUpsert } from "@/lib/mobile-builder-api";
import {
  MOBILE_FEATURES,
  SECTOR_SCREEN_HINTS,
} from "@/lib/mobile-builder-api";

export function Step3Features({
  value,
  onChange,
  disabled,
}: {
  value: MobileAppUpsert;
  onChange: (next: MobileAppUpsert) => void;
  disabled?: boolean;
}) {
  const sectorScreens = SECTOR_SCREEN_HINTS[value.sector] ?? [];
  const featureScreens = MOBILE_FEATURES.filter((f) =>
    value.features.includes(f.id),
  ).map((f) => f.label);

  function toggleFeature(id: string) {
    const next = value.features.includes(id)
      ? value.features.filter((x) => x !== id)
      : [...value.features, id];
    onChange({ ...value, features: next });
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-cf-muted">
          Features à activer
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {MOBILE_FEATURES.map((feat) => {
            const active = value.features.includes(feat.id);
            return (
              <button
                key={feat.id}
                type="button"
                disabled={disabled}
                onClick={() => toggleFeature(feat.id)}
                className={[
                  "rounded-card border p-3 text-left transition-all",
                  active
                    ? "border-cyan-500/50 bg-cyan-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <i className={`${feat.icon} mb-2 block text-lg text-cyan-300`} />
                <p className="text-sm font-medium text-white">{feat.label}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-card border border-violet-500/20 bg-violet-500/5 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-violet-300">
          Écrans qui seront générés
        </p>
        <ul className="space-y-1 text-sm text-cf-muted">
          <li>
            <span className="text-white">Secteur ({value.sector}) :</span>{" "}
            {sectorScreens.join(", ")}
          </li>
          {featureScreens.length > 0 ? (
            <li>
              <span className="text-white">Features :</span>{" "}
              {featureScreens.join(", ")}
            </li>
          ) : (
            <li className="text-cf-muted">Aucune feature additionnelle.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
