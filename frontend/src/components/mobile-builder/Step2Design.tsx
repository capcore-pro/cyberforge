import type { MobileAppUpsert } from "@/lib/mobile-builder-api";
import { MobilePhoneMockup } from "./MobilePhoneMockup";
import { SECTOR_SCREEN_HINTS } from "@/lib/mobile-builder-api";

export function Step2Design({
  value,
  onChange,
  disabled,
}: {
  value: MobileAppUpsert;
  onChange: (next: MobileAppUpsert) => void;
  disabled?: boolean;
}) {
  function patch(partial: Partial<MobileAppUpsert>) {
    onChange({ ...value, ...partial });
  }

  const screenHints = SECTOR_SCREEN_HINTS[value.sector] ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
              Couleur primaire
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={value.primary_color}
                onChange={(e) => patch({ primary_color: e.target.value })}
                disabled={disabled}
                className="h-10 w-14 cursor-pointer rounded border border-white/10 bg-transparent"
              />
              <span className="font-mono text-sm text-cf-muted">
                {value.primary_color}
              </span>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
              Couleur secondaire
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={value.secondary_color}
                onChange={(e) => patch({ secondary_color: e.target.value })}
                disabled={disabled}
                className="h-10 w-14 cursor-pointer rounded border border-white/10 bg-transparent"
              />
              <span className="font-mono text-sm text-cf-muted">
                {value.secondary_color}
              </span>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Logo (URL)
          </label>
          <input
            type="url"
            className="cyber-input w-full"
            value={value.logo_url ?? ""}
            onChange={(e) => patch({ logo_url: e.target.value || null })}
            disabled={disabled}
            placeholder="https://..."
          />
          <p className="mt-1 text-xs text-cf-muted">
            URL publique du logo client (PNG/SVG recommandé).
          </p>
        </div>
      </div>

      <div className="flex justify-center rounded-card border border-white/10 bg-[#0f1117]/40 p-4">
        <MobilePhoneMockup
          primaryColor={value.primary_color}
          secondaryColor={value.secondary_color}
          logoUrl={value.logo_url}
          appName={value.name || "Mon App"}
          screens={screenHints}
        />
      </div>
    </div>
  );
}
