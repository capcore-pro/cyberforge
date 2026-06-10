import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

const INPUT =
  "w-full rounded-control border border-white/10 bg-white/5 px-3 py-2.5 pr-10 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none transition-all duration-200";

export type StripeKeyMode = "unset" | "test" | "live";

export function stripePublishableKeyMode(value: string): StripeKeyMode {
  const trimmed = value.trim();
  if (!trimmed) return "unset";
  if (trimmed.startsWith("pk_test_")) return "test";
  if (trimmed.startsWith("pk_live_")) return "live";
  return "unset";
}

export function StripeKeyModeBadge({ mode }: { mode: StripeKeyMode }) {
  if (mode === "test") {
    return (
      <span className="rounded-full border border-amber-400/35 bg-amber-500/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-amber-300">
        Mode test
      </span>
    );
  }
  if (mode === "live") {
    return (
      <span className="rounded-full border border-teal-400/35 bg-teal-500/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-teal-300">
        Mode live
      </span>
    );
  }
  return (
    <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-white/45">
      Non configuré
    </span>
  );
}

interface StripePublishableKeyFieldProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  id?: string;
  label?: string;
  /** Badge doré « Depuis la fiche client » */
  fromClientBadge?: boolean;
  className?: string;
}

export function StripePublishableKeyField({
  value,
  onChange,
  disabled,
  id = "stripe-publishable-key",
  label = "Clé Stripe publishable",
  fromClientBadge = false,
  className = "",
}: StripePublishableKeyFieldProps) {
  const [visible, setVisible] = useState(false);
  const mode = stripePublishableKeyMode(value);

  return (
    <div className={className}>
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <label htmlFor={id} className="text-xs font-semibold uppercase tracking-wide text-white/50">
          {label}
        </label>
        <StripeKeyModeBadge mode={mode} />
        {fromClientBadge ? (
          <span className="rounded-full border border-[#d4a843]/40 bg-[#d4a843]/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-[#d4a843]">
            Depuis la fiche client
          </span>
        ) : null}
      </div>
      <div className="relative">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="pk_live_... ou pk_test_..."
          autoComplete="off"
          spellCheck={false}
          className={INPUT}
        />
        <button
          type="button"
          disabled={disabled}
          onClick={() => setVisible((v) => !v)}
          className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-white/40 transition hover:text-[#d4a843] disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={visible ? "Masquer la clé" : "Afficher la clé"}
          tabIndex={-1}
        >
          {visible ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
        </button>
      </div>
    </div>
  );
}
