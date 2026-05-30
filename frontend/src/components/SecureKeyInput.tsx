import { Clipboard, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { copyTextToClipboard } from "@/lib/generation-export";

interface SecureKeyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  autoComplete?: string;
}

/** Champ clé secrète éditable — masqué par défaut, révéler / copier. */
export function SecureKeyInput({
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  autoComplete = "off",
}: SecureKeyInputProps) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!value.trim()) return;
    try {
      await copyTextToClipboard(value.trim());
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  const iconBtnClass =
    "flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-cf-border-input text-cf-muted transition hover:border-cf-gold/50 hover:text-cf-gold disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <label className="block space-y-1.5">
      <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
        {label}
      </span>
      <div className="flex items-center gap-2 rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={autoComplete}
          className="min-w-0 flex-1 bg-transparent font-mono text-sm text-cf-text placeholder:text-cf-muted focus:outline-none disabled:opacity-60"
        />
        <div className="flex shrink-0 items-center gap-1.5">
          {copied ? (
            <span className="whitespace-nowrap text-xs font-medium text-cf-gold">
              Copié !
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            disabled={disabled || !value}
            className={iconBtnClass}
            aria-label={visible ? "Masquer" : "Afficher"}
          >
            {visible ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
          </button>
          <button
            type="button"
            onClick={() => void handleCopy()}
            disabled={disabled || !value.trim()}
            className={iconBtnClass}
            aria-label="Copier"
          >
            <Clipboard size={16} aria-hidden />
          </button>
        </div>
      </div>
    </label>
  );
}
