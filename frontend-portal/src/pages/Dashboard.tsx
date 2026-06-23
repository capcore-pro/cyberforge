import type { Client, Site } from "../App";

interface Props {
  client: Client;
  sites: Site[];
  onEditSite: (site: Site) => void;
  onLogout: () => void;
}

export default function Dashboard({ client, sites, onEditSite, onLogout }: Props) {
  const planLabel =
    (
      {
        trial: "Essai",
        essentiel: "Essentiel",
        business: "Business",
        studio: "Studio",
        starter: "Starter",
        pro: "Pro",
        agency: "Agence",
      } as Record<string, string>
    )[client.plan] || client.plan;

  const planColor =
    (
      {
        trial: "text-gray-400",
        essentiel: "text-blue-400",
        business: "text-purple-400",
        studio: "text-orange-400",
        starter: "text-blue-400",
        pro: "text-purple-400",
        agency: "text-orange-400",
      } as Record<string, string>
    )[client.plan] || "text-gray-400";

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Bonjour {client.full_name.split(" ")[0]} 👋
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            {client.company || client.email} ·{" "}
            <span className={planColor}>Plan {planLabel}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="text-gray-500 hover:text-white text-sm transition-colors"
        >
          Déconnexion
        </button>
      </div>

      <h2 className="text-lg font-semibold text-white mb-4">
        Mes sites ({sites.length})
      </h2>

      {sites.length === 0 && (
        <div className="bg-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">Aucun site pour le moment.</p>
          <p className="text-gray-600 text-sm mt-1">
            Contactez CapCore pour créer votre site.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {sites.map((site) => (
          <div
            key={site.id}
            className="bg-gray-800 rounded-2xl p-5 flex items-center justify-between"
          >
            <div>
              <p className="text-white font-semibold">{site.site_name}</p>
              {site.site_url && (
                <a
                  href={site.site_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 text-sm hover:underline"
                >
                  {site.site_url}
                </a>
              )}
              {site.last_deployed_at && (
                <p className="text-gray-500 text-xs mt-1">
                  Mis à jour le{" "}
                  {new Date(site.last_deployed_at).toLocaleDateString("fr-FR")}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onEditSite(site)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white
                         text-sm rounded-lg transition-colors"
            >
              ✏️ Modifier
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
