import type { ReactNode } from "react";

export type BadgeVariant = "gold" | "teal" | "amber" | "red" | "blue" | "gray";
export type BadgeSize = "sm" | "md";

export interface BadgeProps {
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  pulse?: boolean;
  className?: string;
  children: ReactNode;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  gold: "bg-cf-gold/10 text-cf-gold border-cf-gold/20",
  teal: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  red: "bg-red-500/10 text-red-400 border-red-500/20",
  blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  gray: "bg-white/5 text-white/50 border-white/10",
};

const DOT_CLASSES: Record<BadgeVariant, string> = {
  gold: "bg-cf-gold",
  teal: "bg-teal-400",
  amber: "bg-amber-400",
  red: "bg-red-400",
  blue: "bg-blue-400",
  gray: "bg-white/50",
};

const SIZE_CLASSES: Record<BadgeSize, string> = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-3 py-1",
};

function cn(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Badge({
  variant = "gray",
  size = "sm",
  dot = false,
  pulse = false,
  className,
  children,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
    >
      {dot ? (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            DOT_CLASSES[variant],
            pulse ? "animate-pulse" : "",
          )}
          aria-hidden
        />
      ) : null}
      {children}
    </span>
  );
}
