// frontend-portal/src/pages/ForgotPassword.tsx

import { useState } from "react";
import { Link } from "react-router-dom";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://cyberforge-backend-production.up.railway.app";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email) return;
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/portal-onboarding/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch {
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="text-5xl mb-4">📧</div>
          <h1 className="text-2xl font-bold text-white mb-3">Email envoyé !</h1>
          <p className="text-gray-400 mb-6">
            Si cet email est associé à un compte, vous recevrez un lien de
            réinitialisation dans quelques minutes.
          </p>
          <Link to="/login" className="text-blue-400 hover:text-blue-300 text-sm">
            ← Retour à la connexion
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="inline-block bg-gradient-to-br from-amber-500 to-amber-700 rounded-xl px-4 py-2 mb-6">
            <span className="text-white font-black text-xl tracking-widest">
              ⚡ CAPCORE
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Mot de passe oublié ?
          </h1>
          <p className="text-gray-400 text-sm">
            Entrez votre email pour recevoir un lien de réinitialisation.
          </p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSubmit()}
              placeholder="votre@email.com"
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 transition-colors"
            />
          </div>

          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={loading || !email}
            className="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Envoi..." : "Envoyer le lien →"}
          </button>

          <div className="text-center mt-4">
            <Link
              to="/login"
              className="text-gray-500 hover:text-gray-400 text-sm"
            >
              ← Retour à la connexion
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
