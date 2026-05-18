import { useEffect, useState } from "react";
import { APP_NAME } from "@shared/constants";

/**
 * Page d'accueil — tableau de bord et statut de connexion au backend.
 */
export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<
    "loading" | "online" | "offline"
  >("loading");

  // URL de l'API lue depuis les variables d'environnement Vite (jamais de clé API ici)
  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8001";

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health`, {
          signal: controller.signal,
        });
        setBackendStatus(response.ok ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    }

    void checkHealth();
    return () => controller.abort();
  }, [apiBaseUrl]);

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
