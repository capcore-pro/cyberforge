import type { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
}

/**
 * Mise en page principale : zone plein écran et pied de page système.
 */
export function Layout({ children }: LayoutProps) {
  const version = window.cyberforge?.getVersion() ?? "—";
  const platform = window.cyberforge?.getPlatform() ?? "—";

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-cyber-bg">
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {children}
      </main>

      <footer className="flex shrink-0 items-center justify-between border-t border-cyber-border bg-cyber-surfaceAlt px-4 py-2 text-xs text-cyber-muted">
        <span>Logiciel desktop IA — usage éthique et légal uniquement</span>
        <span>
          Electron v{version} · {platform}
        </span>
      </footer>
    </div>
  );
}
