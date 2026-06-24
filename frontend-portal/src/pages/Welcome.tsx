// frontend-portal/src/pages/Welcome.tsx
// Page accueil premier login — choix plan autonome ou géré — MAJ62

import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://cyberforge-backend-production.up.railway.app";

interface WelcomeProps {
  clientId: string;
  clientName: string;
  siteUrl: string;
  onComplete?: () => void;
}

export default function Welcome({
  clientId,
  clientName,
  siteUrl,
  onComplete,
}: WelcomeProps) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<"autonome" | "gere" | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChoice = async (plan: "autonome" | "gere") => {
    setSelected(plan);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/portal-onboarding/complete-onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, management_plan: plan }),
      });
      if (!res.ok) throw new Error("Erreur lors de la sauvegarde du choix");
      onComplete?.();
      if (plan === "autonome") {
        navigate("/pricing");
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-16">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-3xl font-bold text-white mb-3">
            Bienvenue {clientName} !
          </h1>
          <p className="text-gray-400 text-lg mb-4">
            Votre site est en ligne et prêt à être découvert.
          </p>

          {siteUrl ? (
            <a
              href={siteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 text-blue-400 hover:text-blue-300 text-sm transition-all"
            >
              <span>🌐</span>
              <span className="truncate max-w-xs">{siteUrl}</span>
              <span>→</span>
            </a>
          ) : null}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 mb-6">
          <h2 className="text-xl font-bold text-white text-center mb-2">
            Comment souhaitez-vous gérer votre site ?
          </h2>
          <p className="text-gray-500 text-sm text-center mb-8">
            Vous pourrez changer d'avis à tout moment.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => void handleChoice("autonome")}
              disabled={loading}
              className={`relative rounded-xl border-2 p-6 text-left transition-all ${
                selected === "autonome"
                  ? "border-blue-500 bg-blue-950/30"
                  : "border-gray-700 hover:border-blue-600 bg-gray-800/50"
              } disabled:opacity-50`}
            >
              <div className="text-3xl mb-3">✏️</div>
              <div className="font-bold text-white text-lg mb-1">
                Je gère moi-même
              </div>
              <div className="text-gray-400 text-sm mb-4">
                Modifiez vos textes et photos en toute autonomie depuis votre
                espace.
              </div>
              <ul className="space-y-1 mb-4">
                {[
                  "Modification en 1 clic",
                  "Publication en ~10 secondes",
                  "14 jours gratuits",
                ].map((f) => (
                  <li
                    key={f}
                    className="flex items-center gap-2 text-xs text-gray-400"
                  >
                    <span className="text-green-400">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="text-blue-400 font-semibold text-sm">
                Dès 29€/mois →
              </div>
            </button>

            <button
              type="button"
              onClick={() => void handleChoice("gere")}
              disabled={loading}
              className={`relative rounded-xl border-2 p-6 text-left transition-all ${
                selected === "gere"
                  ? "border-amber-500 bg-amber-950/30"
                  : "border-gray-700 hover:border-amber-600 bg-gray-800/50"
              } disabled:opacity-50`}
            >
              <div className="text-3xl mb-3">🛠️</div>
              <div className="font-bold text-white text-lg mb-1">
                Mat gère pour moi
              </div>
              <div className="text-gray-400 text-sm mb-4">
                Je m'occupe de tout — photos, textes, mises à jour. Vous n'avez
                rien à faire.
              </div>
              <ul className="space-y-1 mb-4">
                {[
                  "2 modifications/mois incluses",
                  "Hébergement + support",
                  "Contact direct avec Mat",
                ].map((f) => (
                  <li
                    key={f}
                    className="flex items-center gap-2 text-xs text-gray-400"
                  >
                    <span className="text-green-400">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="text-amber-400 font-semibold text-sm">
                49€/mois →
              </div>
            </button>
          </div>
        </div>

        {error ? (
          <p className="mb-4 text-center text-sm text-red-400">{error}</p>
        ) : null}

        <p className="text-center text-gray-600 text-xs">
          Pas d'engagement · Changement possible à tout moment · Support inclus
        </p>
      </div>
    </div>
  );
}
