import type { ReactNode } from "react";
import { APP_NAME } from "@shared/constants";
import { NAV_ITEMS, type AppPage } from "@/lib/navigation";

interface AppShellProps {
  currentPage: AppPage;
  onNavigate: (page: AppPage) => void;
  children: ReactNode;
  sidebarFooter?: ReactNode;
}

/**
 * Mise en page avec barre latérale et zone de contenu principale.
 */
export function AppShell({
  currentPage,
  onNavigate,
  children,
  sidebarFooter,
}: AppShellProps) {
  return (
    <div className="flex h-full min-h-0 w-full">
      <aside className="cyber-sidebar">
        <div className="border-b border-cyber-border px-4 py-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
            Navigation
          </p>
          <p className="mt-1 text-xs text-cyber-muted">{APP_NAME}</p>
        </div>

        <nav
          className="flex flex-1 flex-col gap-1 p-3"
          aria-label="Navigation principale"
        >
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={!item.enabled}
              onClick={() => item.enabled && onNavigate(item.id)}
              className={`cyber-nav-item w-full text-left ${
                currentPage === item.id ? "cyber-nav-item-active" : ""
              } ${!item.enabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <span className="text-cyber-accent" aria-hidden>
                {item.icon}
              </span>
              {item.label}
            </button>
          ))}
        </nav>

        {sidebarFooter ?? (
          <div className="border-t border-cyber-border p-4">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Agents actifs
            </p>
            <p className="mt-1 text-2xl font-bold text-cyber-neon">1 / 8</p>
            <p className="text-[10px] text-cyber-muted">CoreMindAI opérationnel</p>
          </div>
        )}
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 bg-cyber-grid bg-cyber-grid opacity-40"
          aria-hidden
        />
        <div className="cyber-scanline" aria-hidden />
        <div className="relative flex-1 overflow-y-auto p-6 md:p-8">{children}</div>
      </div>
    </div>
  );
}
