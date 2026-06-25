import { useEffect, useState } from "react";
import {
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";

const API_BASE = normalizeBackendBaseUrl(
  import.meta.env.VITE_API_BASE_URL?.trim() ||
    import.meta.env.VITE_API_URL?.trim() ||
    DEFAULT_API_BASE_URL,
);

type StatutFilter = "tous" | "active" | "trial" | "expired" | "canceled";
type PlanFilter = "tous" | "essentiel" | "business" | "studio" | "gere";

interface ClientAbonne {
  id: string;
  full_name: string;
  email: string;
  subscription_plan: string | null;
  plan: string | null;
  subscription_status: string | null;
  management_plan: string | null;
  trial_ends_at: string | null;
  subscription_ends_at: string | null;
  created_at: string;
  montant_mois: number;
  type_plan: "abonnement" | "gestion";
}

const PLAN_LABELS: Record<string, string> = {
  essentiel: "Essentiel",
  business: "Business",
  studio: "Studio",
  gere: "Géré CapCore",
};

const PLAN_PRIX: Record<string, number> = {
  essentiel: 29,
  business: 59,
  studio: 119,
  gere: 49,
};

const STATUT_LABELS: Record<string, string> = {
  active: "Actif",
  trial: "Essai",
  expired: "Expiré",
  canceled: "Annulé",
};

const STATUT_COLORS: Record<string, string> = {
  active: "text-green-400 bg-green-400/10",
  trial: "text-amber-400 bg-amber-400/10",
  expired: "text-red-400 bg-red-400/10",
  canceled: "text-gray-400 bg-gray-400/10",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-FR");
}

function formatEur(n: number) {
  return n.toFixed(2).replace(".", ",") + " €";
}

export default function ClientsAbonnesPanel() {
  const [clients, setClients] = useState<ClientAbonne[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtreStatut, setFiltreStatut] = useState<StatutFilter>("tous");
  const [filtrePlan, setFiltrePlan] = useState<PlanFilter>("tous");
  const [recherche, setRecherche] = useState("");

  useEffect(() => {
    void chargerClients();
  }, []);

  async function chargerClients() {
    setLoading(true);
    try {
      const [clientsRes] = await Promise.all([
        fetch(`${API_BASE}/api/portal/clients`).then((r) => r.json()),
        fetch(`${API_BASE}/api/portal/stats`).then((r) => r.json()),
        fetch(`${API_BASE}/api/portal/clients`).then((r) => r.json()),
      ]);

      const rawClients: Record<string, unknown>[] = clientsRes.clients || [];

      const plansGereRes = await fetch(`${API_BASE}/api/portal/management-plans`)
        .then((r) => r.json())
        .catch(() => ({ plans: [] }));
      const plansGere: { client_id?: string; status?: string }[] =
        plansGereRes.plans || [];

      const mapped: ClientAbonne[] = rawClients.map((c) => {
        const planGere = plansGere.find(
          (p) => p.client_id === c.id && p.status === "active",
        );
        const estGere = !!planGere || c.management_plan === "gere";
        const planKey = estGere
          ? "gere"
          : String(c.subscription_plan || c.plan || "").toLowerCase();
        const montant = PLAN_PRIX[planKey] || 0;

        return {
          id: String(c.id),
          full_name: String(c.full_name || c.name || "—"),
          email: String(c.email || ""),
          subscription_plan:
            ((c.subscription_plan || c.plan) as string | null) ?? null,
          plan: (c.plan as string | null) ?? null,
          subscription_status: (c.subscription_status as string | null) || "trial",
          management_plan: (c.management_plan as string | null) ?? null,
          trial_ends_at: (c.trial_ends_at as string | null) ?? null,
          subscription_ends_at: (c.subscription_ends_at as string | null) ?? null,
          created_at: String(c.created_at || ""),
          montant_mois: montant,
          type_plan: estGere ? "gestion" : "abonnement",
        };
      });

      setClients(mapped);
    } catch (e) {
      console.error("Erreur chargement clients abonnés", e);
    } finally {
      setLoading(false);
    }
  }

  const clientsFiltres = clients.filter((c) => {
    const matchStatut =
      filtreStatut === "tous" || c.subscription_status === filtreStatut;
    const matchPlan =
      filtrePlan === "tous" ||
      (filtrePlan === "gere"
        ? c.type_plan === "gestion"
        : (c.subscription_plan || c.plan)?.toLowerCase() === filtrePlan);
    const matchRecherche =
      recherche === "" ||
      c.full_name.toLowerCase().includes(recherche.toLowerCase()) ||
      c.email.toLowerCase().includes(recherche.toLowerCase());
    return matchStatut && matchPlan && matchRecherche;
  });

  const mrrFiltré = clientsFiltres
    .filter((c) => c.subscription_status === "active")
    .reduce((acc, c) => acc + c.montant_mois, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Clients abonnés</h2>
          <p className="mt-1 text-sm text-gray-400">
            {clients.length} client{clients.length > 1 ? "s" : ""} au total
          </p>
        </div>
        <button
          type="button"
          onClick={() => void chargerClients()}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:bg-white/10"
        >
          Actualiser
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Rechercher un client..."
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          className="min-w-48 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-amber-400/50 focus:outline-none"
        />

        <select
          value={filtreStatut}
          onChange={(e) => setFiltreStatut(e.target.value as StatutFilter)}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white focus:border-amber-400/50 focus:outline-none"
        >
          <option value="tous">Tous les statuts</option>
          <option value="active">Actif</option>
          <option value="trial">Essai</option>
          <option value="expired">Expiré</option>
          <option value="canceled">Annulé</option>
        </select>

        <select
          value={filtrePlan}
          onChange={(e) => setFiltrePlan(e.target.value as PlanFilter)}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white focus:border-amber-400/50 focus:outline-none"
        >
          <option value="tous">Tous les plans</option>
          <option value="essentiel">Essentiel — 29 €/mois</option>
          <option value="business">Business — 59 €/mois</option>
          <option value="studio">Studio — 119 €/mois</option>
          <option value="gere">Géré CapCore — 49 €/mois</option>
        </select>

        {filtreStatut !== "tous" || filtrePlan !== "tous" || recherche ? (
          <div className="ml-auto flex items-center gap-2 rounded-lg border border-green-400/20 bg-green-400/10 px-3 py-1.5">
            <span className="text-xs text-gray-400">MRR sélection</span>
            <span className="text-sm font-bold text-green-400">
              {formatEur(mrrFiltré)}
            </span>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="py-12 text-center text-gray-400">Chargement...</div>
      ) : clientsFiltres.length === 0 ? (
        <div className="py-12 text-center text-gray-400">Aucun client trouvé</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Client
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Plan
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Statut
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Montant/mois
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Fin essai / abonnement
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-400">
                  Client depuis
                </th>
              </tr>
            </thead>
            <tbody>
              {clientsFiltres.map((c, i) => (
                <tr
                  key={c.id}
                  className={`border-b border-white/5 transition-colors hover:bg-white/5 ${
                    i % 2 === 0 ? "bg-transparent" : "bg-white/[0.02]"
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{c.full_name}</div>
                    <div className="text-xs text-gray-500">{c.email}</div>
                  </td>

                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-medium ${
                        c.type_plan === "gestion"
                          ? "bg-amber-400/10 text-amber-400"
                          : "bg-blue-400/10 text-blue-400"
                      }`}
                    >
                      {PLAN_LABELS[
                        c.type_plan === "gestion"
                          ? "gere"
                          : (c.subscription_plan || c.plan)?.toLowerCase() || ""
                      ] ||
                        c.subscription_plan ||
                        c.plan ||
                        "—"}
                    </span>
                  </td>

                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-medium ${
                        STATUT_COLORS[c.subscription_status || ""] ||
                        "bg-gray-400/10 text-gray-400"
                      }`}
                    >
                      {STATUT_LABELS[c.subscription_status || ""] ||
                        c.subscription_status ||
                        "—"}
                    </span>
                  </td>

                  <td className="px-4 py-3">
                    <span className="font-medium text-white">
                      {c.montant_mois > 0 ? formatEur(c.montant_mois) : "—"}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-gray-400">
                    {formatDate(c.trial_ends_at || c.subscription_ends_at)}
                  </td>

                  <td className="px-4 py-3 text-gray-400">
                    {formatDate(c.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
