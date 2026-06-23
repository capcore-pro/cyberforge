// frontend-portal/src/pages/Pricing.tsx

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getPlans, createCheckout } from "../lib/stripe-api";

const PLAN_ORDER = ["essentiel", "business", "studio"];

const PLAN_COLORS: Record<string, string> = {
  essentiel: "from-slate-700 to-slate-900",
  business: "from-blue-700 to-blue-900",
  studio: "from-violet-700 to-violet-900",
};

const PLAN_BADGE: Record<string, string | null> = {
  essentiel: null,
  business: "Le plus populaire",
  studio: null,
};

export default function Pricing() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Record<string, any>>({});
  const [interval, setInterval] = useState<"monthly" | "yearly">("monthly");
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [trialDays, setTrialDays] = useState(14);

  const clientId = localStorage.getItem("portal_client_id") || "";

  useEffect(() => {
    getPlans()
      .then((data) => {
        setPlans(data.plans);
        setTrialDays(data.trial_days);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = async (planKey: string) => {
    if (!clientId) {
      navigate("/login");
      return;
    }
    setCheckoutLoading(planKey);
    try {
      const result = await createCheckout(clientId, planKey, interval);
      window.location.href = result.checkout_url;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erreur checkout";
      alert("Erreur : " + message);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const getPrice = (planKey: string) => {
    const plan = plans[planKey];
    if (!plan) return 0;
    return interval === "monthly"
      ? plan.monthly_price_eur
      : plan.yearly_price_eur;
  };

  const getSavings = (planKey: string) => {
    const plan = plans[planKey];
    if (!plan) return 0;
    const monthlyTotal = plan.monthly_price_eur * 12;
    const yearly = plan.yearly_price_eur;
    return Math.round(monthlyTotal - yearly);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm animate-pulse">
          Chargement des plans…
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-3">
          Choisissez votre plan
        </h1>
        <p className="text-gray-400 text-lg mb-2">
          {trialDays} jours d&apos;essai gratuit inclus — sans carte bancaire
        </p>
        <p className="text-gray-500 text-sm">
          Modifiez votre site en autonomie, redéployez en 10 secondes.
        </p>

        <div className="inline-flex items-center gap-3 mt-8 bg-gray-900 rounded-full px-2 py-2">
          <button
            type="button"
            onClick={() => setInterval("monthly")}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
              interval === "monthly"
                ? "bg-white text-gray-900"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Mensuel
          </button>
          <button
            type="button"
            onClick={() => setInterval("yearly")}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
              interval === "yearly"
                ? "bg-white text-gray-900"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Annuel
            <span className="ml-2 text-xs bg-green-500 text-white px-2 py-0.5 rounded-full">
              -30%
            </span>
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {PLAN_ORDER.map((planKey) => {
          const plan = plans[planKey];
          if (!plan) return null;
          const badge = PLAN_BADGE[planKey];
          const isPopular = planKey === "business";
          const price = getPrice(planKey);
          const savings = getSavings(planKey);

          return (
            <div
              key={planKey}
              className={`relative rounded-2xl border ${
                isPopular
                  ? "border-blue-500 shadow-lg shadow-blue-500/20"
                  : "border-gray-800"
              } bg-gray-900 p-6 flex flex-col`}
            >
              {badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-blue-600 text-white text-xs font-semibold px-4 py-1 rounded-full">
                    {badge}
                  </span>
                </div>
              )}

              <div
                className={`bg-gradient-to-br ${PLAN_COLORS[planKey]} rounded-xl p-4 mb-5`}
              >
                <div className="text-white font-bold text-lg">{plan.name}</div>
                <div className="text-gray-300 text-xs mt-1">
                  {plan.description}
                </div>
              </div>

              <div className="mb-5">
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-white">
                    {interval === "yearly" ? Math.round(price / 12) : price}€
                  </span>
                  <span className="text-gray-400 text-sm">/mois</span>
                </div>
                {interval === "yearly" && (
                  <div className="text-sm text-gray-400 mt-1">
                    {price}€ facturés annuellement
                    {savings > 0 && (
                      <span className="ml-2 text-green-400 font-medium">
                        Économisez {savings}€
                      </span>
                    )}
                  </div>
                )}
                {interval === "monthly" && (
                  <div className="text-xs text-gray-500 mt-1">
                    ou {plan.yearly_price_eur}€/an (économisez {savings}€)
                  </div>
                )}
              </div>

              <ul className="space-y-2 mb-6 flex-1">
                {plan.features.map((feature: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-300"
                  >
                    <span className="text-green-400 mt-0.5 shrink-0">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                type="button"
                onClick={() => void handleSubscribe(planKey)}
                disabled={checkoutLoading === planKey}
                className={`w-full py-3 rounded-xl font-semibold text-sm transition-all ${
                  isPopular
                    ? "bg-blue-600 hover:bg-blue-500 text-white"
                    : "bg-gray-800 hover:bg-gray-700 text-white"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {checkoutLoading === planKey
                  ? "Redirection…"
                  : `Démarrer — ${trialDays} jours gratuits`}
              </button>
              <p className="text-center text-xs text-gray-500 mt-2">
                Sans carte bancaire pendant l&apos;essai
              </p>
            </div>
          );
        })}
      </div>

      <p className="text-center text-gray-600 text-xs mt-10">
        Résiliation possible à tout moment · Paiement sécurisé Stripe · TVA FR
        incluse
      </p>
    </div>
  );
}
