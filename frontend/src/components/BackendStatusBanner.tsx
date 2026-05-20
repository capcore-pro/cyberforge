import { useBackendHealth } from "@/context/BackendHealthContext";

/**
 * Bandeau visible quand FastAPI est injoignable (reconnexion automatique en cours).
 */
export function BackendStatusBanner() {
  const { status } = useBackendHealth();

  if (status !== "offline") return null;

  return (
    <div
      className="shrink-0 border-b border-amber-400/40 bg-amber-400/10 px-4 py-2 text-center text-xs text-amber-200"
      role="status"
    >
      Backend hors ligne — reconnexion automatique toutes les 3&nbsp;s. Les actions
      API échoueront jusqu&apos;au retour du serveur sur le port&nbsp;8002.
    </div>
  );
}
