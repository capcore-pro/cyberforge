import { listSectorsForKind } from "@/lib/sector-presets";
import type { GeneratorKindId } from "@/lib/generator-kinds";
import type { StudioProjectKind } from "@/lib/studio-types";

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4 text-left transition";

const DIGITAL_SECTOR = {
  id: "digital",
  label: "Digital & Agence",
  description: "Sites, apps, logiciels pour agences digitales",
  emoji: "⚡",
};

interface SectorSelectorProps {
  kind: StudioProjectKind;
  value: string | null;
  onSelect: (sectorId: string) => void;
  disabled?: boolean;
}

export function SectorSelector({
  kind,
  value,
  onSelect,
  disabled,
}: SectorSelectorProps) {
  const presets =
    kind === "video"
      ? []
      : listSectorsForKind(kind as GeneratorKindId);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSelect(DIGITAL_SECTOR.id)}
        className={[
          V2_CARD,
          "relative flex min-h-[110px] flex-col items-start",
          value === DIGITAL_SECTOR.id
            ? "border-[#f59e0b] shadow-[0_0_16px_rgba(245,158,11,0.2)] ring-1 ring-[#f59e0b]/40"
            : "hover:border-[rgba(0,212,255,0.25)]",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ].join(" ")}
      >
        <span className="absolute right-3 top-3 rounded-full border border-[#f59e0b]/40 bg-[#f59e0b]/15 px-2 py-0.5 text-[10px] font-semibold text-[#f59e0b]">
          CapCore
        </span>
        <span className="mb-2 text-2xl" aria-hidden>
          {DIGITAL_SECTOR.emoji}
        </span>
        <span className="text-sm font-semibold text-cf-text">
          {DIGITAL_SECTOR.label}
        </span>
        <span className="mt-1 text-xs text-cf-muted">{DIGITAL_SECTOR.description}</span>
      </button>

      {presets.map((preset) => {
        const selected = value === preset.id;
        return (
          <button
            key={preset.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(preset.id)}
            className={[
              V2_CARD,
              "flex min-h-[110px] flex-col items-start",
              selected
                ? "border-cf-cyan shadow-glow-cyan ring-1 ring-cf-cyan/30"
                : "hover:border-[rgba(0,212,255,0.25)]",
              disabled ? "cursor-not-allowed opacity-60" : "",
            ].join(" ")}
          >
            <span className="mb-2 text-2xl" aria-hidden>
              {preset.emoji}
            </span>
            <span className="text-sm font-semibold text-cf-text">{preset.label}</span>
            <span className="mt-1 line-clamp-2 text-xs text-cf-muted">
              {preset.description}
            </span>
          </button>
        );
      })}

      {kind === "video" ? (
        <div className="col-span-full rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4 text-sm text-cf-muted">
          Le secteur « Digital & Agence » est recommandé pour les clips vidéo CapCore.
        </div>
      ) : null}
    </div>
  );
}
