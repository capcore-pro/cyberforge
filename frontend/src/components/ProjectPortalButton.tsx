// frontend/src/components/ProjectPortalButton.tsx
// Bouton "Créer accès portail" sur fiche projet livré sans compte portail — MAJ62

import { useCallback, useEffect, useState } from "react";
import DeliverModal from "./DeliverModal";
import { buildBackendApiUrl } from "@/lib/backend-url";

interface ProjectPortalButtonProps {
  projectName: string;
  siteUrl: string;
  isDelivered: boolean;
}

type PortalCheckResult = {
  exists?: boolean;
  name?: string;
  email?: string;
  subscription_status?: string;
  management_plan?: string | null;
};

type PortalStatus = "loading" | "none" | "exists";

export default function ProjectPortalButton({
  projectName,
  siteUrl,
  isDelivered,
}: ProjectPortalButtonProps) {
  const [status, setStatus] = useState<PortalStatus>("loading");
  const [portalInfo, setPortalInfo] = useState<PortalCheckResult | null>(null);
  const [showModal, setShowModal] = useState(false);

  const checkPortal = useCallback(async () => {
    if (!siteUrl.trim()) return;
    setStatus("loading");
    try {
      const res = await fetch(
        buildBackendApiUrl(
          `/api/portal-onboarding/check?site_url=${encodeURIComponent(siteUrl.trim())}`,
        ),
      );
      const data = (await res.json()) as PortalCheckResult;
      if (data.exists) {
        setPortalInfo(data);
        setStatus("exists");
      } else {
        setPortalInfo(null);
        setStatus("none");
      }
    } catch {
      setPortalInfo(null);
      setStatus("none");
    }
  }, [siteUrl]);

  useEffect(() => {
    if (!isDelivered || !siteUrl) return;
    void checkPortal();
  }, [isDelivered, siteUrl, checkPortal]);

  if (!isDelivered) return null;

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 text-gray-600 text-xs animate-pulse">
        <span>Vérification portail...</span>
      </div>
    );
  }

  if (status === "exists" && portalInfo) {
    const statusColors: Record<string, string> = {
      trial: "text-blue-400",
      active: "text-green-400",
      expired: "text-red-400",
      canceled: "text-gray-400",
    };
    const statusLabels: Record<string, string> = {
      trial: "Essai en cours",
      active: "Abonnement actif",
      expired: "Essai expiré",
      canceled: "Annulé",
    };
    const subStatus = portalInfo.subscription_status || "";
    const colorClass = statusColors[subStatus] || "text-gray-400";
    const label = statusLabels[subStatus] || subStatus || "—";

    return (
      <div className="flex items-center gap-3 bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3">
        <div className="flex-1">
          <p className="text-gray-400 text-xs mb-0.5">Accès portail</p>
          <p className="text-white text-sm font-semibold">{portalInfo.name}</p>
          <p className="text-gray-500 text-xs">{portalInfo.email}</p>
        </div>
        <div className="text-right">
          <span className={`text-xs font-semibold ${colorClass}`}>
            ● {label}
          </span>
          {portalInfo.management_plan ? (
            <p className="text-gray-600 text-xs mt-0.5 capitalize">
              {portalInfo.management_plan === "gere"
                ? "🛠️ Géré par Mat"
                : "✏️ Autonome"}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-600/40 hover:border-blue-500 text-blue-400 hover:text-blue-300 rounded-xl px-4 py-3 text-sm font-semibold transition-all w-full"
      >
        <span>🔑</span>
        <span>Créer accès portail pour ce client</span>
        <span className="ml-auto">→</span>
      </button>

      {showModal ? (
        <DeliverModal
          projectName={projectName}
          siteUrl={siteUrl}
          portalOnly
          onClose={() => setShowModal(false)}
          onDelivered={() => {
            setShowModal(false);
            void checkPortal();
          }}
        />
      ) : null}
    </>
  );
}
