import { DEFAULT_API_BASE_URL } from "@shared/constants";
import { isElectronApiAvailable } from "@/lib/api-client";
import { useBackendHealth } from "@/context/BackendHealthContext";

/**
 * Configuration générale de l'application desktop.
 */
export function GeneralSettingsPanel() {
  const { status, health } = useBackendHealth();
  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const transport = import.meta.env.DEV
    ? "HTTP via proxy Vite"
    : isElectronApiAvailable()
      ? "IPC vers FastAPI"
      : "HTTP direct";

  const backendLabel =
    status === "online"
      ? "En ligne"
      : status === "offline"
        ? "Hors ligne"
        : "Connexion…";

  return (
    <section className="cyber-panel space-y-4 p-5">
      <h2 className="text-sm font-semibold text-cyber-text">Configuration générale</h2>
      <dl className="grid gap-3 text-sm">
        <div className="flex justify-between gap-4 border-b border-cyber-border/60 pb-2">
          <dt className="text-cyber-muted">Backend FastAPI</dt>
          <dd
            className={
              status === "online"
                ? "font-medium text-emerald-400"
                : status === "offline"
                  ? "font-medium text-red-300"
                  : "text-cyber-muted"
            }
          >
            {backendLabel}
          </dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-cyber-border/60 pb-2">
          <dt className="text-cyber-muted">URL API</dt>
          <dd className="max-w-[55%] truncate font-mono text-[10px] text-cyber-violet">
            {apiBaseUrl}
          </dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-cyber-border/60 pb-2">
          <dt className="text-cyber-muted">Transport</dt>
          <dd className="text-cyber-text">{transport}</dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-cyber-border/60 pb-2">
          <dt className="text-cyber-muted">Version API</dt>
          <dd className="text-cyber-text">
            {health?.version ? `v${health.version}` : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-cyber-muted">Langue interface</dt>
          <dd className="text-cyber-text">Français</dd>
        </div>
      </dl>
      <p className="text-xs text-cyber-muted">
        Les soldes API et fournisseurs externes se gèrent dans l&apos;onglet{" "}
        <strong className="text-cyber-neon">Cockpit</strong> (portefeuille, seuils,
        fournisseurs).
      </p>
    </section>
  );
}
