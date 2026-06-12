import { useEffect, useId, useRef, useState } from "react";

export interface DropdownOption {
  value: string;
  label: string;
  icon?: string;
  disabled?: boolean;
}

export interface DropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  className?: string;
}

function cn(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Dropdown({
  options,
  value,
  onChange,
  placeholder = "Sélectionner…",
  label,
  disabled,
  className,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, [open]);

  function selectOption(option: DropdownOption) {
    if (option.disabled) return;
    onChange(option.value);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className={cn("relative flex flex-col gap-1", className)}>
      {label ? (
        <span className="text-xs uppercase tracking-widest text-white/50">
          {label}
        </span>
      ) : null}

      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-[var(--cf-radius-control)]",
          "border border-[var(--cf-border-input)] bg-[var(--cf-bg-secondary)] px-3 py-2 text-sm",
          "text-[var(--cf-text-primary)] transition-colors",
          "focus:border-[var(--cf-gold)] focus:outline-none",
          "disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        <span className={cn("truncate", !selected ? "text-white/30" : "")}>
          {selected?.label ?? placeholder}
        </span>
        <i
          className={cn(
            "ti ti-chevron-down shrink-0 text-white/40 transition-transform",
            open ? "rotate-180" : "",
          )}
          aria-hidden
        />
      </button>

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-xl border border-white/10 bg-[var(--cf-bg-card)] shadow-2xl"
        >
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <li key={option.value} role="option" aria-selected={isSelected}>
                <button
                  type="button"
                  disabled={option.disabled}
                  onClick={() => selectOption(option)}
                  className={cn(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition",
                    "hover:bg-white/5",
                    isSelected ? "bg-cf-gold/10 text-cf-gold" : "text-white/80",
                    option.disabled ? "cursor-not-allowed opacity-40" : "",
                  )}
                >
                  {option.icon ? (
                    <i className={cn("text-base", option.icon)} aria-hidden />
                  ) : null}
                  <span className="truncate">{option.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
