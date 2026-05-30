import { Clipboard, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { copyTextToClipboard } from "@/lib/generation-export";

const MASK = "●●●●●●●●";

interface PasswordRevealFieldProps {
  password: string | null | undefined;
  label?: string;
  className?: string;
  emptyLabel?: string;
}

/**
 * Champ mot de passe en lecture seule — masqué par défaut, révéler / copier.
 */
export function PasswordRevealField({
  password,
  label = "Mot de passe",
  className = "",
  emptyLabel = "—",
}: PasswordRevealFieldProps) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const value = password?.trim() ?? "";
  const hasValue = value.length > 0;

  async function handleCopy() {
    if (!hasValue) return;
    try {
      await copyTextToClipboard(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  const iconBtnClass =
    "flex h-8 w-8 items-center justify-center rounded-control border border-cf-border-input text-cf-muted transition hover:border-cf-gold/50 hover:text-cf-gold disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className={className}>
      {label ? (
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-cf-label">
          {label}
        </p>
      ) : null}
      <div className="flex items-center gap-2 rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2">
        <span
          className="min-w-0 flex-1 truncate font-mono text-sm text-cf-text"
          aria-live="polite"
        >
          {!hasValue ? (
            <span className="text-cf-muted">{emptyLabel}</span>
          ) : visible ? (
            value
          ) : (
            MASK
          )}
        </span>
        <div className="flex shrink-0 items-center gap-1.5">
          {copied ? (
            <span className="whitespace-nowrap text-xs font-medium text-cf-gold">
              Copié !
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            disabled={!hasValue}
            className={iconBtnClass}
            aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
          >
            {visible ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
          </button>
          <button
            type="button"
            onClick={() => void handleCopy()}
            disabled={!hasValue}
            className={iconBtnClass}
            aria-label="Copier le mot de passe"
          >
            <Clipboard size={16} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}
