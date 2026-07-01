import { useBackendHealth } from "@/context/BackendHealthContext";

/**
 * Bandeau visible quand FastAPI est injoignable (reconnexion automatique en cours).
 */
export function BackendStatusBanner() {
  const { status } = useBackendHealth();

  if (status !== "offline") return null;

  return (
    <div
      className="shrink-0 border-b border-cf-alert/30 bg-cf-alert/10 px-4 py-2 text-center text-xs text-cf-alert"
      role="status"
    >
      Backend hors ligne — reconnexion automatique. Les actions API échoueront
      jusqu&apos;au retour du serveur sur le port&nbsp;8002.
    </div>
  );
}
