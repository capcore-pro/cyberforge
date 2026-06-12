import { useState, type ChangeEvent } from "react";

export interface InputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "password" | "email" | "number";
  error?: string;
  hint?: string;
  icon?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

function cn(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Input({
  label,
  placeholder,
  value,
  onChange,
  type = "text",
  error,
  hint,
  icon,
  disabled,
  required,
  className,
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword && showPassword ? "text" : type;

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onChange(event.target.value);
  }

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label ? (
        <label className="text-xs uppercase tracking-widest text-white/50">
          {label}
          {required ? <span className="text-cf-gold"> *</span> : null}
        </label>
      ) : null}

      <div className="relative">
        {icon ? (
          <i
            className={cn(
              "pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/30",
              icon,
            )}
            aria-hidden
          />
        ) : null}

        <input
          type={inputType}
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          className={cn(
            "w-full rounded-[var(--cf-radius-control)] border px-3 py-2 text-sm transition-colors",
            "bg-[var(--cf-bg-secondary)] border-[var(--cf-border-input)] text-[var(--cf-text-primary)]",
            "placeholder:text-white/30 focus:border-[var(--cf-gold)] focus:outline-none",
            "disabled:cursor-not-allowed disabled:opacity-50",
            icon ? "pl-9" : "",
            isPassword ? "pr-9" : "",
          )}
        />

        {isPassword ? (
          <button
            type="button"
            tabIndex={-1}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 transition hover:text-white/60"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
          >
            <i className={showPassword ? "ti ti-eye-off" : "ti ti-eye"} aria-hidden />
          </button>
        ) : null}
      </div>

      {error ? <p className="mt-1 text-xs text-red-400">{error}</p> : null}
      {!error && hint ? (
        <p className="mt-1 text-xs text-white/30">{hint}</p>
      ) : null}
    </div>
  );
}
