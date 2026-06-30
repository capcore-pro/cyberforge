import { useCallback, useEffect, useState } from "react";
import {
  deactivateLicense,
  getBuildStatus,
  listBuilds,
  listLicenses,
  startBuild,
  type ElectronBuildStatus,
  type ElectronBuildStatusValue,
  type ElectronLicenseRow,
} from "@/lib/electron-api";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

type TabId = "new" | "builds" | "licenses";

const STATUS_COLOR: Record<ElectronBuildStatusValue, string> = {
  pending: "text-yellow-400",
  building: "text-blue-400",
  success: "text-green-400",
  failed: "text-red-400",
};

const STATUS_LABEL: Record<ElectronBuildStatusValue, string> = {
  pending: "En attente",
  building: "Compilation",
  success: "Terminé",
  failed: "Échec",
};

export function DesktopBuilder() {
  const [tab, setTab] = useState<TabId>("new");
  const [builds, setBuilds] = useState<ElectronBuildStatus[]>([]);
  const [licenses, setLicenses] = useState<ElectronLicenseRow[]>([]);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentBuild, setCurrentBuild] = useState<ElectronBuildStatus | null>(null);
  const [notifyBuildId, setNotifyBuildId] = useState<string | null>(null);
  const [notifyNotes, setNotifyNotes] = useState("");
  const [notifySending, setNotifySending] = useState(false);
  const [notifySuccess, setNotifySuccess] = useState(false);

  const [form, setForm] = useState({
    client_name: "",
    client_email: "",
    app_name: "",
    app_description: "",
    model: "one_shot" as "one_shot" | "subscription",
    price_one_shot: 2000,
    price_monthly: 29,
    version: "1.0.0",
  });

  const loadBuilds = useCallback(async () => {
    try {
      const data = await listBuilds();
      setBuilds(data.builds);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement des builds impossible.");
    }
  }, []);

  const loadLicenses = useCallback(async () => {
    try {
      const data = await listLicenses();
      setLicenses(data.licenses);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement des licences impossible.");
    }
  }, []);

  useEffect(() => {
    if (tab === "builds") void loadBuilds();
    if (tab === "licenses") void loadLicenses();
  }, [tab, loadBuilds, loadLicenses]);

  useEffect(() => {
    if (
      !currentBuild ||
      currentBuild.build_status === "success" ||
      currentBuild.build_status === "failed"
    ) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const updated = await getBuildStatus(currentBuild.id);
        setCurrentBuild(updated);
        if (updated.build_status === "success" || updated.build_status === "failed") {
          void loadBuilds();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Polling build impossible.");
      }
    }, 15_000);

    return () => window.clearInterval(interval);
  }, [currentBuild, loadBuilds]);

  async function handleBuild() {
    if (!form.client_name || !form.app_name || !form.client_email || !form.app_description) {
      return;
    }

    setBuilding(true);
    setError(null);
    try {
      const result = await startBuild({
        ...form,
        project_id: `desktop-${Date.now()}`,
      });
      const status = await getBuildStatus(result.build_id);
      setCurrentBuild(status);
      setTab("builds");
      await loadBuilds();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lancement du build impossible.");
    } finally {
      setBuilding(false);
    }
  }

  async function handleDeactivate(licenseKey: string) {
    setError(null);
    try {
      await deactivateLicense(licenseKey);
      await loadLicenses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Désactivation impossible.");
    }
  }

  async function handleNotifyClient() {
    if (!notifyBuildId || notifySending) return;
    setNotifySending(true);
    try {
      const res = await fetch(`${API_BASE}/api/electron/notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          build_id: notifyBuildId,
          notes_maj: notifyNotes,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setNotifySuccess(true);
        await loadBuilds();
        setTimeout(() => {
          setNotifyBuildId(null);
          setNotifyNotes("");
          setNotifySuccess(false);
        }, 2500);
      }
    } catch (e) {
      console.error("Erreur notification client", e);
    } finally {
      setNotifySending(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Desktop Builder</h1>
        <p className="mt-1 text-sm text-gray-400">
          Génère des logiciels Windows .exe pour tes clients
        </p>
      </div>

      {error ? (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      ) : null}

      {currentBuild &&
      (currentBuild.build_status === "pending" ||
        currentBuild.build_status === "building") ? (
        <div className="mb-4 rounded-lg border border-blue-500/30 bg-blue-500/10 px-4 py-3 text-sm text-blue-200">
          Compilation en cours — <strong>{currentBuild.app_name}</strong> (
          {STATUS_LABEL[currentBuild.build_status]})
        </div>
      ) : null}

      <div className="mb-6 flex gap-2 border-b border-gray-700">
        {(
          [
            ["new", "+ Nouveau"],
            ["builds", "Compilations"],
            ["licenses", "Licences"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === id
                ? "border-b-2 border-blue-400 text-blue-400"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "new" ? (
        <div className="space-y-4 rounded-xl bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-white">
            Nouveau logiciel client
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm text-gray-400">Nom du client *</label>
              <input
                className="w-full rounded-lg bg-gray-700 px-3 py-2 text-sm text-white"
                placeholder="Dupont Plomberie"
                value={form.client_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, client_name: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">Email client *</label>
              <input
                type="email"
                className="w-full rounded-lg bg-gray-700 px-3 py-2 text-sm text-white"
                placeholder="client@email.com"
                value={form.client_email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, client_email: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">Nom du logiciel *</label>
              <input
                className="w-full rounded-lg bg-gray-700 px-3 py-2 text-sm text-white"
                placeholder="GestionPro"
                value={form.app_name}
                onChange={(e) => setForm((f) => ({ ...f, app_name: e.target.value }))}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">Version</label>
              <input
                className="w-full rounded-lg bg-gray-700 px-3 py-2 text-sm text-white"
                placeholder="1.0.0"
                value={form.version}
                onChange={(e) => setForm((f) => ({ ...f, version: e.target.value }))}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm text-gray-400">
              Description du logiciel *
            </label>
            <textarea
              className="h-24 w-full resize-none rounded-lg bg-gray-700 px-3 py-2 text-sm text-white"
              placeholder="Logiciel de gestion pour un plombier : clients, devis, interventions, factures..."
              value={form.app_description}
              onChange={(e) =>
                setForm((f) => ({ ...f, app_description: e.target.value }))
              }
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-gray-400">Modèle commercial</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, model: "one_shot" }))}
                className={`rounded-lg border p-4 text-left transition-colors ${
                  form.model === "one_shot"
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-gray-600 hover:border-gray-500"
                }`}
              >
                <p className="text-sm font-medium text-white">One Shot</p>
                <p className="mt-1 text-xs text-gray-400">
                  Paiement unique — licence permanente
                </p>
                <input
                  type="number"
                  className="mt-2 w-full rounded bg-gray-700 px-2 py-1 text-sm text-white"
                  placeholder="Prix (EUR)"
                  value={form.price_one_shot}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      price_one_shot: Number(e.target.value),
                    }))
                  }
                  onClick={(e) => e.stopPropagation()}
                />
              </button>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, model: "subscription" }))}
                className={`rounded-lg border p-4 text-left transition-colors ${
                  form.model === "subscription"
                    ? "border-orange-500 bg-orange-500/10"
                    : "border-gray-600 hover:border-gray-500"
                }`}
              >
                <p className="text-sm font-medium text-white">One Shot + Abonnement</p>
                <p className="mt-1 text-xs text-gray-400">
                  Vérification licence au démarrage
                </p>
                <div className="mt-2 flex gap-2">
                  <input
                    type="number"
                    className="w-1/2 rounded bg-gray-700 px-2 py-1 text-sm text-white"
                    placeholder="Prix unique"
                    value={form.price_one_shot}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        price_one_shot: Number(e.target.value),
                      }))
                    }
                    onClick={(e) => e.stopPropagation()}
                  />
                  <input
                    type="number"
                    className="w-1/2 rounded bg-gray-700 px-2 py-1 text-sm text-white"
                    placeholder="EUR/mois"
                    value={form.price_monthly}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        price_monthly: Number(e.target.value),
                      }))
                    }
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleBuild()}
            disabled={
              building ||
              !form.client_name ||
              !form.app_name ||
              !form.client_email ||
              !form.app_description
            }
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            {building ? "Génération en cours…" : "Générer et compiler le .exe"}
          </button>
        </div>
      ) : null}

      {tab === "builds" ? (
        <div className="space-y-3">
          {builds.length === 0 ? (
            <p className="py-8 text-center text-gray-500">Aucun build pour l&apos;instant</p>
          ) : null}
          {builds.map((build) => (
            <div
              key={build.id}
              className="flex items-center justify-between rounded-xl bg-gray-800 p-4"
            >
              <div>
                <p className="font-medium text-white">{build.app_name}</p>
                <p className="text-sm text-gray-400">
                  {build.client_name} · {build.client_email}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {build.model === "one_shot" ? "One Shot" : "Abonnement"} · v
                  {build.version}
                </p>
              </div>
              <div className="text-right">
                <p
                  className={`text-sm font-medium ${
                    STATUS_COLOR[build.build_status] ?? "text-gray-400"
                  }`}
                >
                  {STATUS_LABEL[build.build_status] ?? build.build_status}
                </p>
                {build.license_key ? (
                  <p className="mt-1 font-mono text-xs text-gray-500">
                    {build.license_key}
                  </p>
                ) : null}
                {build.download_url ? (
                  <a
                    href={build.download_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block rounded-lg bg-green-600 px-3 py-1 text-xs text-white transition-colors hover:bg-green-700"
                  >
                    Télécharger .exe
                  </a>
                ) : null}
                {build.download_url && build.client_email ? (
                  <div className="mt-2 flex flex-col items-end gap-1">
                    {build.notified_at ? (
                      <p className="text-xs text-green-400">
                        ✓ Client notifié automatiquement
                      </p>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => {
                        setNotifyBuildId(build.id);
                        setNotifyNotes("");
                      }}
                      className="flex items-center gap-1 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-xs font-medium text-amber-400 transition-colors hover:bg-amber-400/20"
                    >
                      <i className="ti ti-bell" />
                      {build.notified_at ? "Renvoyer la notification" : "Notifier le client"}
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {tab === "licenses" ? (
        <div className="space-y-3">
          {licenses.length === 0 ? (
            <p className="py-8 text-center text-gray-500">Aucune licence pour l&apos;instant</p>
          ) : null}
          {licenses.map((lic) => (
            <div
              key={lic.id}
              className="flex items-center justify-between rounded-xl bg-gray-800 p-4"
            >
              <div>
                <p className="font-mono text-sm text-white">{lic.license_key}</p>
                <p className="text-sm text-gray-400">{lic.client_email}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {lic.model === "one_shot" ? "One Shot" : "Abonnement"}
                  {lic.electron_builds?.app_name
                    ? ` · ${lic.electron_builds.app_name}`
                    : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-sm font-medium ${
                    lic.is_active ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {lic.is_active ? "Active" : "Inactive"}
                </span>
                {lic.is_active && lic.model === "subscription" ? (
                  <button
                    type="button"
                    onClick={() => void handleDeactivate(lic.license_key)}
                    className="rounded-lg border border-red-600/30 bg-red-600/20 px-3 py-1 text-xs text-red-400 transition-colors hover:bg-red-600/40"
                  >
                    Désactiver
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Modal notification mise à jour */}
      {notifyBuildId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md space-y-4 rounded-2xl border border-white/10 bg-[#1a1a2e] p-6">
            {notifySuccess ? (
              <div className="space-y-3 py-4 text-center">
                <div className="text-4xl">✅</div>
                <p className="font-semibold text-white">Email envoyé au client !</p>
                <p className="text-sm text-gray-400">
                  Notification de mise à jour envoyée avec succès.
                </p>
              </div>
            ) : (
              <>
                <div>
                  <h3 className="text-lg font-bold text-white">Notifier le client</h3>
                  <p className="mt-1 text-sm text-gray-400">
                    Un email de mise à jour sera envoyé automatiquement.
                  </p>
                </div>

                <div>
                  <label className="mb-1 block text-xs text-gray-500">
                    Notes de mise à jour{" "}
                    <span className="text-gray-600">(optionnel)</span>
                  </label>
                  <textarea
                    value={notifyNotes}
                    onChange={(e) => setNotifyNotes(e.target.value)}
                    placeholder="Ex : correction d'un bug sur l'export PDF, amélioration des performances..."
                    rows={3}
                    className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-amber-400/50 focus:outline-none"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setNotifyBuildId(null)}
                    className="flex-1 rounded-xl border border-white/10 bg-white/5 py-2.5 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10"
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleNotifyClient()}
                    disabled={notifySending}
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-amber-400 py-2.5 text-sm font-bold text-black transition-colors hover:bg-amber-300 disabled:opacity-50"
                  >
                    {notifySending ? (
                      <>
                        <i className="ti ti-loader animate-spin" />
                        Envoi...
                      </>
                    ) : (
                      <>
                        <i className="ti ti-send" />
                        Envoyer la notification
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
