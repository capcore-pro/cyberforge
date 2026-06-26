// frontend/src/components/ProjectPortalButton.tsx
// Bouton "Créer accès portail" sur fiche projet livré sans compte portail — MAJ62

import { useCallback, useEffect, useState } from "react";
import DeliverModal from "./DeliverModal";
import { buildBackendApiUrl } from "@/lib/backend-url";
import { switchToAutonome } from "@/lib/portal-management-api";

interface ProjectPortalButtonProps {
  projectName: string;
  siteUrl: string;
  isDelivered: boolean;
}

type PortalCheckResult = {
  exists?: boolean;
  client_id?: string;
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
  const [portalData, setPortalData] = useState<PortalCheckResult | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [switchDone, setSwitchDone] = useState(false);

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
        setPortalData(data);
        setStatus("exists");
      } else {
        setPortalData(null);
        setStatus("none");
      }
    } catch {
      setPortalData(null);
      setStatus("none");
    }
  }, [siteUrl]);

  useEffect(() => {
    if (!isDelivered || !siteUrl) return;
    void checkPortal();
  }, [isDelivered, siteUrl, checkPortal]);

  const handleBackToAutonome = async () => {
    if (!portalData?.client_id) return;
    setSwitching(true);
    const res = await switchToAutonome(portalData.client_id);
    if (res.success) {
      setSwitchDone(true);
      setPortalData((prev) =>
        prev ? { ...prev, management_plan: "autonome" } : prev,
      );
    }
    setSwitching(false);
  };

  if (!isDelivered) return null;

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 text-gray-600 text-xs animate-pulse">
        <span>Vérification portail...</span>
      </div>
    );
  }

  if (status === "exists" && portalData) {
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
    const subStatus = portalData.subscription_status || "";
    const colorClass = statusColors[subStatus] || "text-gray-400";
    const label = statusLabels[subStatus] || subStatus || "—";

    return (
      <div className="flex items-center gap-3 bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3">
        <div className="flex-1">
          <p className="text-gray-400 text-xs mb-0.5">Accès portail</p>
          <p className="text-white text-sm font-semibold">{portalData.name}</p>
          <p className="text-gray-500 text-xs">{portalData.email}</p>
        </div>
        <div className="text-right min-w-[140px]">
          <span className={`text-xs font-semibold ${colorClass}`}>
            ● {label}
          </span>
          {portalData.management_plan ? (
            <p className="text-gray-600 text-xs mt-0.5 capitalize">
              {portalData.management_plan === "gere"
                ? "🛠️ Géré par Mat"
                : "✏️ Autonome"}
            </p>
          ) : null}
          {portalData.management_plan === "gere" && !switchDone && (
            <button
              type="button"
              onClick={() => void handleBackToAutonome()}
              disabled={switching}
              className="mt-2 w-full px-3 py-1.5 rounded-lg bg-white/5 text-white/50 text-xs hover:bg-white/10 hover:text-white disabled:opacity-40 transition-colors"
            >
              {switching ? "En cours..." : "↩ Repasser en autonome"}
            </button>
          )}
          {switchDone && (
            <p className="mt-2 text-xs text-green-400">
              ✅ Client repassé en autonome — email envoyé
            </p>
          )}
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
