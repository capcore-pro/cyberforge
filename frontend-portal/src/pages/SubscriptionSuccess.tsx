// frontend-portal/src/pages/SubscriptionSuccess.tsx

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function SubscriptionSuccess() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => navigate("/dashboard"), 4000);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl mb-6">🎉</div>
        <h1 className="text-3xl font-bold text-white mb-3">Abonnement activé !</h1>
        <p className="text-gray-400 mb-2">Votre plan est maintenant actif.</p>
        <p className="text-gray-500 text-sm">
          Redirection vers votre tableau de bord…
        </p>
      </div>
    </div>
  );
}
