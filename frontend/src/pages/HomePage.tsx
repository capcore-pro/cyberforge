import { useEffect, useState } from "react";
import { APP_NAME, DEFAULT_API_BASE_URL } from "@shared/constants";
import { apiRequest, isElectronApiAvailable } from "@/lib/api-client";

/**
 * Page d'accueil — tableau de bord et statut de connexion au backend.
 */
export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<
    "loading" | "online" | "offline"
  >("loading");

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const transportLabel = isElectronApiAvailable()
    ? "IPC → FastAPI"
    : "HTTP direct";

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      const response = await apiRequest<{ status?: string }>({
        method: "GET",
        path: "/api/health",
      });
      if (!cancelled) {
        setBackendStatus(response.ok ? "online" : "offline");
      }
    }

    void checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel = {
    loading: "Vérification…",
    online: "Backend connecté",
    offline: "Backend indisponible",
  }[backendStatus];

  const statusColor = {
    loading: "text-cyber-muted",
    online: "text-green-400",
    offline: "text-red-400",
  }[backendStatus];

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div className="cyber-panel">
        <h2 className="mb-2 text-lg font-semibold">Bienvenue sur {APP_NAME}</h2>
        <p className="text-sm text-cyber-muted">
          Plateforme desktop d&apos;assistance IA pour la cybersécurité.
          Configurez votre fichier <code className="text-cyber-accent">.env</code>{" "}
          à la racine du projet avant d&apos;utiliser les agents.
        </p>
      </div>

      <div className="cyber-panel flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">État du backend</p>
          <p className={`text-xs ${statusColor}`}>{statusLabel}</p>
          <p className="mt-1 text-xs text-cyber-muted">{transportLabel}</p>
        </div>
        <span className="text-xs text-cyber-muted">{apiBaseUrl}</span>
      </div>

      <div className="flex gap-3">
        <button type="button" className="cyber-btn" disabled>
          Agents (bientôt)
        </button>
        <button type="button" className="cyber-btn opacity-50" disabled>
          Outils (bientôt)
        </button>
      </div>
    </section>
  );
}
