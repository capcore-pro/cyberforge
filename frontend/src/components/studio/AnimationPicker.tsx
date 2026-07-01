export const ANIMATION_OPTIONS = [
  { id: "none", label: "Aucune", className: "" },
  { id: "fade-in", label: "Apparition douce", className: "animate-fade-in" },
  { id: "slide-up", label: "Glissement vers le haut", className: "animate-slide-up" },
  { id: "zoom-in", label: "Zoom avant", className: "animate-zoom-in" },
  { id: "parallax", label: "Parallax", className: "animate-parallax" },
  { id: "count-up", label: "Compteurs animés", className: "animate-count-up" },
  { id: "glitch", label: "Effet glitch", className: "animate-glitch" },
] as const;

interface AnimationPickerProps {
  value: string;
  onChange: (animationClass: string) => void;
  disabled?: boolean;
}

export function AnimationPicker({
  value,
  onChange,
  disabled,
}: AnimationPickerProps) {
  return (
    <div className="space-y-2">
      <p className="font-mono text-xs text-cf-cyan">// animations</p>
      <div className="space-y-1.5">
        {ANIMATION_OPTIONS.map((opt) => {
          const selected =
            value === opt.className ||
            (opt.id === "none" && !value);
          return (
            <button
              key={opt.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.className)}
              className={[
                "flex w-full items-center gap-2 rounded-control border px-2.5 py-2 text-left text-xs transition",
                selected
                  ? "border-cf-cyan/40 bg-cf-cyan/10 text-cf-cyan"
                  : "border-[rgba(0,212,255,0.1)] bg-[#0d0d14] text-cf-muted hover:border-cf-cyan/25",
                disabled ? "opacity-50" : "",
              ].join(" ")}
            >
              <span
                className={[
                  "h-6 w-8 shrink-0 rounded border border-[rgba(0,212,255,0.15)] bg-[#0a0a12]",
                  opt.className,
                ].join(" ")}
                aria-hidden
              />
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
