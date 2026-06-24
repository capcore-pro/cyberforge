import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Client, Site } from "../App";

const API =
  import.meta.env.VITE_API_URL ||
  "https://cyberforge-backend-production.up.railway.app";

interface Props {
  onLogin: (client: Client, sites: Site[]) => void;
}

function normalizeSite(row: Record<string, unknown>): Site {
  return {
    id: String(row.id ?? ""),
    site_name: String(row.site_name ?? ""),
    site_url: String(row.site_url ?? ""),
    html_content: String(row.html_content ?? ""),
    sector: String(row.sector ?? ""),
    project_type: String(row.project_type ?? "vitrine_next"),
    last_deployed_at: String(row.last_deployed_at ?? ""),
  };
}

export default function Login({ onLogin }: Props) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin() {
    if (!email || !password) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API}/api/portal/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Erreur de connexion");
        return;
      }

      onLogin(
        {
          id: String(data.client.id ?? ""),
          email: String(data.client.email ?? ""),
          full_name: String(data.client.full_name ?? ""),
          company: String(data.client.company ?? ""),
          plan: String(data.client.plan ?? "trial"),
          subscription_status: String(
            data.client.subscription_status ?? "trial",
          ),
          trial_ends_at: data.client.trial_ends_at ?? null,
          subscription_ends_at: data.client.subscription_ends_at ?? null,
          billing_interval: String(data.client.billing_interval ?? "monthly"),
          onboarding_done: data.client.onboarding_done !== false,
          site_url: String(
            data.client.site_url ??
              (data.sites as Record<string, unknown>[])[0]?.site_url ??
              "",
          ),
        },
        (data.sites as Record<string, unknown>[]).map(normalizeSite),
      );
      const onboardingDone = data.client.onboarding_done !== false;
      navigate(onboardingDone ? "/dashboard" : "/welcome");
    } catch {
      setError("Impossible de se connecter au serveur");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">⚡ CapCore</h1>
          <p className="text-gray-400 mt-2">Espace client</p>
        </div>

        <div className="bg-gray-800 rounded-2xl p-6 space-y-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Email</label>
            <input
              type="email"
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2.5"
              placeholder="votre@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-1 block">
              Mot de passe
            </label>
            <input
              type="password"
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2.5"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleLogin()}
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="button"
            onClick={() => void handleLogin()}
            disabled={loading || !email || !password}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50
                       text-white font-medium rounded-lg transition-colors"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>

          <div className="text-center mt-3">
            <Link
              to="/forgot-password"
              className="text-gray-500 hover:text-gray-400 text-xs"
            >
              Mot de passe oublié ?
            </Link>
          </div>
        </div>

        <p className="text-center text-gray-600 text-xs mt-4">
          Accès fourni par CapCore Studio Digital
        </p>
      </div>
    </div>
  );
}
