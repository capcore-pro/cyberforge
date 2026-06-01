import { Eye, EyeOff } from "lucide-react";
import { useState, type InputHTMLAttributes } from "react";

interface PasswordInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  /** Classes appliquées au conteneur (flex-1 recommandé dans une ligne). */
  containerClassName?: string;
}

/**
 * Champ de saisie mot de passe avec bouton œil afficher / masquer.
 */
export function PasswordInput({
  className = "",
  containerClassName = "",
  disabled,
  ...inputProps
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  const inputClass =
    "min-w-0 flex-1 rounded-control border border-cf-border-input bg-cf-card px-3 py-2 pr-10 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-50 " +
    className;

  return (
    <div className={`relative min-w-0 ${containerClassName}`.trim()}>
      <input
        {...inputProps}
        type={visible ? "text" : "password"}
        disabled={disabled}
        className={inputClass}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => setVisible((v) => !v)}
        className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-cf-muted transition hover:text-cf-gold disabled:cursor-not-allowed disabled:opacity-40"
        aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
        tabIndex={-1}
      >
        {visible ? (
          <EyeOff size={16} aria-hidden />
        ) : (
          <Eye size={16} aria-hidden />
        )}
      </button>
    </div>
  );
}
