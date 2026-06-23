// frontend-portal/src/components/SubscriptionBanner.tsx

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSubscriptionStatus, SubscriptionStatus } from "../lib/stripe-api";

interface Props {
  clientId: string;
}

export default function SubscriptionBanner({ clientId }: Props) {
  const navigate = useNavigate();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    if (!clientId) return;
    getSubscriptionStatus(clientId)
      .then(setStatus)
      .catch(console.error);
  }, [clientId]);

  if (!status) return null;

  if (status.status === "active") return null;

  if (status.status === "trial" && status.trial_days_left !== undefined) {
    return (
      <div className="bg-blue-900/40 border-b border-blue-700/50 px-4 py-2 flex items-center justify-between text-sm">
        <span className="text-blue-300">
          ✦ Mode essai —{" "}
          <span className="font-semibold">
            {status.trial_days_left} jour{status.trial_days_left > 1 ? "s" : ""}{" "}
            restant{status.trial_days_left > 1 ? "s" : ""}
          </span>{" "}
          avant expiration
        </span>
        <button
          type="button"
          onClick={() => navigate("/pricing")}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded-full transition-all"
        >
          Choisir un plan →
        </button>
      </div>
    );
  }

  if (
    status.status === "expired" ||
    status.status === "canceled" ||
    status.status === "none"
  ) {
    return (
      <div className="bg-red-900/40 border-b border-red-700/50 px-4 py-3 flex items-center justify-between text-sm">
        <span className="text-red-300">
          ⚠ Votre essai a expiré — Souscrivez pour continuer à modifier votre
          site
        </span>
        <button
          type="button"
          onClick={() => navigate("/pricing")}
          className="bg-red-600 hover:bg-red-500 text-white text-xs px-3 py-1 rounded-full transition-all"
        >
          Voir les plans →
        </button>
      </div>
    );
  }

  return null;
}
