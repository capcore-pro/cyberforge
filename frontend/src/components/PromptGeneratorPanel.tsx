import { useCallback, useState } from "react";
import type { GeneratorKindId } from "@/lib/generator-kinds";
import { generateCyberforgePrompt } from "@/lib/generator-prompt-api";
import { apiErrorMessage } from "@/lib/api-errors";

const PROMPT_KIND_OPTIONS: { id: GeneratorKindId; label: string }[] = [
  { id: "vitrine", label: "Vitrine" },
  { id: "ecommerce", label: "E-commerce" },
  { id: "reservation", label: "Réservation" },
  { id: "app_web", label: "App Web" },
  { id: "desktop", label: "Desktop" },
  { id: "extension", label: "Extension" },
];

export interface PromptGeneratorPanelProps {
  disabled?: boolean;
  selectedKind: GeneratorKindId;
  onSelectKind: (kind: GeneratorKindId) => void;
  onPromptGenerated: (prompt: string) => void;
}

export function PromptGeneratorPanel({
  disabled = false,
  selectedKind,
  onSelectKind,
  onPromptGenerated,
}: PromptGeneratorPanelProps) {
  const [open, setOpen] = useState(false);
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    const trimmed = idea.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre idée en quelques mots (3 caractères minimum).");
      return;
    }
    setBusy(true);
    setError(null);
    const response = await generateCyberforgePrompt({
      project_kind: selectedKind,
      idea: trimmed,
    });
    setBusy(false);
    if (!response.ok || !response.data?.prompt?.trim()) {
      setError(
        apiErrorMessage(
          response,
          "Impossible de générer le prompt. Vérifiez la clé Anthropic dans Paramètres.",
        ),
      );
      return;
    }
    onPromptGenerated(response.data.prompt.trim());
    setOpen(false);
  }, [idea, onPromptGenerated, selectedKind]);

  return (
    <div className="mb-4 rounded-control border border-cf-gold/30 bg-gradient-to-br from-cf-active/80 to-cf-secondary/40 shadow-gold/10">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-cf-active/60 disabled:cursor-not-allowed disabled:opacity-60"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold tracking-wide text-cf-gold">
          ✨ GÉNÉRER UN PROMPT
        </span>
        <span
          className="text-xs text-cf-muted"
          aria-hidden
        >
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open ? (
        <div className="border-t border-cf-gold/20 px-4 pb-4 pt-3">
          <label className="mb-3 block">
            <span className="mb-2 block text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Type de projet
            </span>
            <select
              value={selectedKind}
              disabled={disabled || busy}
              onChange={(e) => onSelectKind(e.target.value as GeneratorKindId)}
              className="w-full rounded-control border border-cf-border-input bg-cf-main px-3 py-2.5 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
            >
              {PROMPT_KIND_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="mb-3 block">
            <span className="mb-2 block text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Votre idée
            </span>
            <textarea
              rows={4}
              value={idea}
              disabled={disabled || busy}
              onChange={(e) => {
                setIdea(e.target.value);
                setError(null);
              }}
              placeholder="Décris ton idée brièvement…"
              className="w-full resize-y rounded-control border border-cf-border-input bg-cf-main px-3 py-2.5 text-sm leading-relaxed text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
            />
          </label>

          {error ? (
            <p className="mb-3 text-sm text-red-300" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="button"
            disabled={disabled || busy || idea.trim().length < 3}
            onClick={() => void handleGenerate()}
            className="w-full rounded-control border border-cf-gold bg-cf-gold px-4 py-2.5 text-sm font-semibold text-cf-main transition hover:bg-cf-gold-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? "Génération…" : "Générer le prompt"}
          </button>

          <p className="mt-2 text-[11px] leading-relaxed text-cf-muted">
            Le prompt sera injecté dans le champ description ci-dessous (Claude Sonnet).
          </p>
        </div>
      ) : null}
    </div>
  );
}
