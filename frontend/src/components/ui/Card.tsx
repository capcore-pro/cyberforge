import type { ReactNode } from "react";

export type CardPadding = "none" | "sm" | "md" | "lg";

export interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: string;
  actions?: ReactNode;
  padding?: CardPadding;
  hoverable?: boolean;
  onClick?: () => void;
  className?: string;
  children: ReactNode;
}

const PADDING_CLASSES: Record<CardPadding, string> = {
  none: "p-0",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

function cn(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  title,
  subtitle,
  icon,
  actions,
  padding = "md",
  hoverable = false,
  onClick,
  className,
  children,
}: CardProps) {
  const clickable = Boolean(onClick);
  const Tag = clickable ? "button" : "div";

  return (
    <Tag
      type={clickable ? "button" : undefined}
      onClick={onClick}
      className={cn(
        "w-full rounded-[var(--cf-radius-card)] border text-left",
        "bg-[var(--cf-bg-card)] border-[var(--cf-border)]",
        PADDING_CLASSES[padding],
        hoverable || clickable
          ? "cursor-pointer transition-all duration-200 hover:border-white/20 hover:bg-white/[0.02]"
          : "",
        className,
      )}
    >
      {title ? (
        <header className="mb-3 flex items-start justify-between gap-3 border-b border-white/5 pb-3">
          <div className="flex min-w-0 items-start gap-2">
            {icon ? (
              <i className={cn("text-lg text-cf-gold", icon)} aria-hidden />
            ) : null}
            <div className="min-w-0">
              <h3 className="text-sm font-medium text-white">{title}</h3>
              {subtitle ? (
                <p className="mt-0.5 text-xs text-white/40">{subtitle}</p>
              ) : null}
            </div>
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </header>
      ) : null}
      {children}
    </Tag>
  );
}
