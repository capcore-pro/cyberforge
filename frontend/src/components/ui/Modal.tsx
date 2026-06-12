import { useEffect, type ReactNode } from "react";

export type ModalSize = "sm" | "md" | "lg" | "xl";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  icon?: string;
  size?: ModalSize;
  footer?: ReactNode;
  children: ReactNode;
}

const SIZE_CLASSES: Record<ModalSize, string> = {
  sm: "max-w-[400px]",
  md: "max-w-[560px]",
  lg: "max-w-[720px]",
  xl: "max-w-[900px]",
};

const BODY_PADDING: Record<ModalSize, string> = {
  sm: "px-4 py-3",
  md: "px-5 py-4",
  lg: "px-6 py-5",
  xl: "px-6 py-5",
};

function cn(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  icon,
  size = "md",
  footer,
  children,
}: ModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cf-modal-title"
        className={cn(
          "w-full rounded-xl border border-white/10 bg-[var(--cf-bg-card)] shadow-2xl",
          SIZE_CLASSES[size],
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-white/5 px-5 py-4">
          <div className="flex min-w-0 items-start gap-3">
            {icon ? (
              <i className={cn("mt-0.5 text-xl text-cf-gold", icon)} aria-hidden />
            ) : null}
            <div className="min-w-0">
              <h2 id="cf-modal-title" className="text-base font-semibold text-white">
                {title}
              </h2>
              {subtitle ? (
                <p className="mt-1 text-sm text-white/40">{subtitle}</p>
              ) : null}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-control border border-white/10 bg-white/5 px-2 py-1 text-white/60 transition hover:text-white"
            aria-label="Fermer"
          >
            <i className="ti ti-x" aria-hidden />
          </button>
        </header>

        <div
          className={cn(
            "max-h-[70vh] overflow-y-auto",
            BODY_PADDING[size],
          )}
        >
          {children}
        </div>

        {footer ? (
          <footer className="border-t border-white/5 px-5 pb-5 pt-4">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>
  );
}
