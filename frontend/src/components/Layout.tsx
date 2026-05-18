import type { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
}

/**
 * Mise en page principale : en-tête, zone de contenu, pied de page.
 */
export function Layout({ children }: LayoutProps) {
  const version = window.cyberforge?.getVersion() ?? "—";
  const platform = window.cyberforge?.getPlatform() ?? "—";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-cyber-border bg-cyber-surface px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight text-cyber-accent">
            CyberForge
          </h1>
          <span className="text-xs text-cyber-muted">
            v{version} · {platform}
          </span>
        </div>
      </header>

      <main className="flex-1 p-6">{children}</main>

      <footer className="border-t border-cyber-border px-6 py-3 text-center text-xs text-cyber-muted">
        Logiciel desktop IA — usage éthique et légal uniquement
      </footer>
    </div>
  );
}
