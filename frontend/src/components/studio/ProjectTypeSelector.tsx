import {
  GENERATOR_KINDS,
  GENERATOR_KIND_VISUAL,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import type { StudioProjectKind } from "@/lib/studio-types";

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4 text-left transition";

const VIDEO_KIND = {
  id: "video" as const,
  label: "🎬 Vidéo Kling",
  description: "Clip vidéo IA pour réseaux sociaux",
  emoji: "🎬",
};

interface ProjectTypeSelectorProps {
  value: StudioProjectKind | null;
  onSelect: (kind: StudioProjectKind) => void;
  disabled?: boolean;
}

export function ProjectTypeSelector({
  value,
  onSelect,
  disabled,
}: ProjectTypeSelectorProps) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {GENERATOR_KINDS.map((kind) => {
        const visual = GENERATOR_KIND_VISUAL[kind.id as GeneratorKindId];
        const selected = value === kind.id;
        return (
          <button
            key={kind.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(kind.id)}
            className={[
              V2_CARD,
              "flex min-h-[120px] flex-col items-start",
              selected
                ? "border-cf-cyan shadow-glow-cyan ring-1 ring-cf-cyan/30"
                : "hover:border-[rgba(0,212,255,0.25)]",
              disabled ? "cursor-not-allowed opacity-60" : "",
            ].join(" ")}
          >
            <span className="mb-2 text-2xl" aria-hidden>
              {visual.emoji}
            </span>
            <span className="text-sm font-semibold text-cf-text">{kind.title}</span>
            <span className="mt-1 text-xs leading-snug text-cf-muted">
              {visual.shortDescription}
            </span>
          </button>
        );
      })}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSelect("video")}
        className={[
          V2_CARD,
          "flex min-h-[120px] flex-col items-start",
          value === "video"
            ? "border-cf-cyan shadow-glow-cyan ring-1 ring-cf-cyan/30"
            : "hover:border-[rgba(0,212,255,0.25)]",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ].join(" ")}
      >
        <span className="mb-2 text-2xl" aria-hidden>
          {VIDEO_KIND.emoji}
        </span>
        <span className="text-sm font-semibold text-cf-text">{VIDEO_KIND.label}</span>
        <span className="mt-1 text-xs leading-snug text-cf-muted">
          {VIDEO_KIND.description}
        </span>
      </button>
    </div>
  );
}
