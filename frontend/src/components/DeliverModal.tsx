// frontend/src/components/DeliverModal.tsx
// Modal de livraison — propose création compte portail — MAJ62

import { useState } from "react";
import { buildBackendApiUrl } from "@/lib/backend-url";

interface DeliverModalProps {
  projectName: string;
  siteUrl: string;
  onClose: () => void;
  onDelivered: (options?: { keepModalOpen?: boolean }) => void | Promise<void>;
  portalOnly?: boolean;
}

type PortalResult = {
  created?: boolean;
  reason?: string;
  message?: string;
  email_sent?: boolean;
};

export default function DeliverModal({
  projectName,
  siteUrl,
  onClose,
  onDelivered,
  portalOnly = false,
}: DeliverModalProps) {
  const [step, setStep] = useState<"confirm" | "portal" | "success">(
    portalOnly ? "portal" : "confirm",
  );
  const [clientEmail, setClientEmail] = useState("");
  const [clientName, setClientName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PortalResult | null>(null);

  const handleDeliverOnly = () => {
    void Promise.resolve(onDelivered()).finally(() => onClose());
  };

  const handleCreatePortal = async () => {
    if (!clientEmail || !clientName) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        buildBackendApiUrl("/api/portal-onboarding/create-account"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: clientEmail,
            name: clientName,
            site_url: siteUrl,
            project_name: projectName,
            send_email: true,
          }),
        },
      );
      const data = (await res.json()) as PortalResult & { detail?: string };
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Création impossible",
        );
      }
      setResult(data);
      setStep("success");
      await Promise.resolve(onDelivered({ keepModalOpen: true }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 px-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-lg w-full shadow-2xl">
        {step === "confirm" && !portalOnly ? (
          <>
            <div className="text-center mb-6">
              <div className="text-4xl mb-3">🚀</div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Livrer le projet
              </h2>
              <p className="text-gray-400 text-sm">
                <span className="text-white font-semibold">{projectName}</span>{" "}
                sera livré sans watermark.
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mb-6">
              <p className="text-gray-400 text-xs mb-1">URL du site livré</p>
              <a
                href={siteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 text-sm hover:text-blue-300 break-all"
              >
                {siteUrl}
              </a>
            </div>

            <p className="text-white font-semibold text-center mb-4">
              Créer un accès portail pour ce client ?
            </p>
            <p className="text-gray-500 text-xs text-center mb-6">
              Le client pourra modifier son site en autonomie depuis
              client.capcore.pro
            </p>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <button
                type="button"
                onClick={() => setStep("portal")}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all text-sm"
              >
                ✅ Oui, créer l&apos;accès
              </button>
              <button
                type="button"
                onClick={handleDeliverOnly}
                className="bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold py-3 rounded-xl transition-all text-sm"
              >
                Non, livrer sans portail
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="w-full text-gray-600 hover:text-gray-500 text-xs py-2"
            >
              Annuler
            </button>
          </>
        ) : null}

        {step === "portal" && (
          <>
            <div className="text-center mb-6">
              <div className="text-4xl mb-3">👤</div>
              <h2 className="text-2xl font-bold text-white mb-2">
                Infos du client
              </h2>
              <p className="text-gray-400 text-sm">
                L&apos;email et le mot de passe temporaire seront envoyés
                automatiquement.
              </p>
            </div>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-gray-400 text-sm mb-2">
                  Nom du client
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="Jean Dupont"
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">
                  Email du client
                </label>
                <input
                  type="email"
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                  placeholder="client@email.com"
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            {error ? (
              <p className="mb-4 text-center text-xs text-red-300">{error}</p>
            ) : null}

            <button
              type="button"
              onClick={() => void handleCreatePortal()}
              disabled={loading || !clientEmail || !clientName}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 mb-3"
            >
              {loading
                ? "Création en cours..."
                : "Créer l'accès & envoyer l'email →"}
            </button>

            <button
              type="button"
              onClick={() => (portalOnly ? onClose() : setStep("confirm"))}
              className="w-full text-gray-600 hover:text-gray-500 text-xs py-2"
            >
              {portalOnly ? "Annuler" : "← Retour"}
            </button>
          </>
        )}

        {step === "success" && (
          <div className="text-center">
            <div className="text-5xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-white mb-3">Projet livré !</h2>
            {result?.created !== false ? (
              <>
                <p className="text-gray-400 text-sm mb-2">
                  Accès portail créé pour{" "}
                  <span className="text-white font-semibold">{clientEmail}</span>
                </p>
                <p className="text-gray-500 text-xs mb-6">
                  L&apos;email de bienvenue avec les identifiants a été envoyé
                  automatiquement.
                </p>
              </>
            ) : (
              <p className="text-gray-400 text-sm mb-6">
                {result?.message || "Projet livré avec succès."}
              </p>
            )}
            <button
              type="button"
              onClick={onClose}
              className="bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 px-8 rounded-xl transition-all"
            >
              Fermer
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
