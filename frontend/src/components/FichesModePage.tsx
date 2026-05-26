import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  DEMO_STATUS_LABELS,
  createClient,
  deleteClient,
  fetchClientDetail,
  listClients,
  updateClient,
  updateDemoStatus,
  type ClientDetail,
  type ClientKind,
  type ClientRecord,
  type DemoStatusSlug,
} from "@/lib/clients-api";
import { setSelectedClientId } from "@/lib/selected-client";

export interface FichesModePageProps {
  kind: ClientKind;
  onOpenGenerator?: () => void;
}

const MODE_COPY: Record<
  ClientKind,
  {
    sectionLabel: string;
    pageTitle: string;
    subtitle: string;
    listLabel: string;
    newButton: string;
    emptyList: string;
    selectHint: string;
    formNew: string;
    formEdit: string;
    companyLabel: string;
    companyPlaceholder: string;
    demosHeading: string;
    demosEmpty: string;
    deleteConfirm: string;
    loadError: string;
  }
> = {
  client: {
    sectionLabel: "Mode Client",
    pageTitle: "Clients",
    subtitle:
      "Fiches clients, historique des démos partagées et branding automatique à la création.",
    listLabel: "Clients",
    newButton: "Nouveau client",
    emptyList: "Aucun client pour l'instant.",
    selectHint: "Sélectionnez un client ou créez-en un nouveau.",
    formNew: "Nouveau client",
    formEdit: "Fiche client",
    companyLabel: "Entreprise",
    companyPlaceholder: "Raison sociale",
    demosHeading: "Démos envoyées",
    demosEmpty: "Aucune démo liée à ce client.",
    deleteConfirm:
      "Supprimer ce client ? Les démos restent mais ne seront plus liées.",
    loadError: "Impossible de charger les clients.",
  },
  perso: {
    sectionLabel: "Espace perso",
    pageTitle: "Perso",
    subtitle:
      "Créations personnelles de Mat — projets hors client, tests, démos internes et portfolios.",
    listLabel: "Fiches perso",
    newButton: "Nouvelle fiche perso",
    emptyList: "Aucune fiche perso pour l'instant.",
    selectHint: "Sélectionnez une fiche ou créez un projet perso.",
    formNew: "Nouvelle fiche perso",
    formEdit: "Fiche perso",
    companyLabel: "Type / usage",
    companyPlaceholder: "Test interne, portfolio, démo CyberForge…",
    demosHeading: "Démos liées",
    demosEmpty: "Aucune démo liée à cette fiche.",
    deleteConfirm: "Supprimer cette fiche perso ?",
    loadError: "Impossible de charger les fiches perso.",
  },
};

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const STATUS_STYLES: Record<DemoStatusSlug, string> = {
  envoyee: "border-slate-400/40 bg-slate-400/10 text-slate-300",
  ouverte: "border-cyan-400/40 bg-cyan-400/10 text-cyan-300",
  interessee: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  validee: "border-green-400/40 bg-green-400/10 text-green-300",
  expiree: "border-amber-400/40 bg-amber-400/10 text-amber-300",
};

function emptyForm(kind: ClientKind): ClientFormState {
  return {
    name: "",
    company: "",
    email: "",
    phone: "",
    primary_color: kind === "perso" ? "#22d3ee" : "#6366f1",
    logo_url: "",
  };
}

interface ClientFormState {
  name: string;
  company: string;
  email: string;
  phone: string;
  primary_color: string;
  logo_url: string;
}

export function PersoTag() {
  return (
    <span className="inline-block rounded-full border border-fuchsia-400/40 bg-fuchsia-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-fuchsia-300">
      Perso
    </span>
  );
}

/**
 * Liste + fiche (clients commerciaux ou fiches perso selon `kind`).
 */
export function FichesModePage({ kind, onOpenGenerator }: FichesModePageProps) {
  const copy = MODE_COPY[kind];
  const isPerso = kind === "perso";

  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [form, setForm] = useState<ClientFormState>(() => emptyForm(kind));
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isNew, setIsNew] = useState(false);

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await listClients(kind);
    setLoading(false);
    if (!response.ok || !response.data) {
      setError(apiErrorMessage(response, copy.loadError));
      return;
    }
    setClients(response.data);
  }, [kind, copy.loadError]);

  const loadDetail = useCallback(async (clientId: string) => {
    setDetailLoading(true);
    const response = await fetchClientDetail(clientId);
    setDetailLoading(false);
    if (!response.ok || !response.data) {
      setError(apiErrorMessage(response, "Impossible de charger la fiche."));
      return;
    }
    const c = response.data;
    setDetail(c);
    setForm({
      name: c.name,
      company: c.company ?? "",
      email: c.email ?? "",
      phone: c.phone ?? "",
      primary_color: c.primary_color ?? emptyForm(kind).primary_color,
      logo_url: c.logo_url ?? "",
    });
  }, [kind]);

  useEffect(() => {
    setSelectedId(null);
    setIsNew(false);
    setDetail(null);
    setForm(emptyForm(kind));
    setError(null);
  }, [kind]);

  useEffect(() => {
    void loadClients();
  }, [loadClients]);

  useEffect(() => {
    if (selectedId && !isNew) {
      void loadDetail(selectedId);
    } else {
      setDetail(null);
    }
  }, [selectedId, isNew, loadDetail]);

  function startNew() {
    setIsNew(true);
    setSelectedId(null);
    setDetail(null);
    setForm(emptyForm(kind));
    setError(null);
  }

  function selectClient(id: string) {
    setIsNew(false);
    setSelectedId(id);
    setError(null);
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    const name = form.name.trim();
    if (!name) {
      setError("Le nom est obligatoire.");
      return;
    }
    setSaving(true);
    setError(null);
    const payload = {
      kind,
      name,
      company: form.company.trim() || null,
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      primary_color: form.primary_color.trim() || null,
      logo_url: form.logo_url.trim() || null,
    };

    if (isNew) {
      const response = await createClient(payload);
      setSaving(false);
      if (!response.ok || !response.data) {
        setError(apiErrorMessage(response, "Création impossible."));
        return;
      }
      setIsNew(false);
      setSelectedId(response.data.id);
      await loadClients();
      return;
    }

    if (!selectedId) return;
    const response = await updateClient(selectedId, payload);
    setSaving(false);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Enregistrement impossible."));
      return;
    }
    await loadClients();
    await loadDetail(selectedId);
  }

  async function handleDelete() {
    if (!selectedId || isNew) return;
    if (!window.confirm(copy.deleteConfirm)) {
      return;
    }
    setSaving(true);
    const response = await deleteClient(selectedId);
    setSaving(false);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Suppression impossible."));
      return;
    }
    setSelectedId(null);
    setIsNew(false);
    await loadClients();
  }

  async function handleDemoStatus(
    demoId: string,
    status: "validee" | "expiree",
  ) {
    const response = await updateDemoStatus(demoId, status);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Mise à jour du statut impossible."));
      return;
    }
    if (selectedId) {
      await loadDetail(selectedId);
    }
  }

  function handleLogoFile(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      if (result.startsWith("data:image/")) {
        setForm((f) => ({ ...f, logo_url: result }));
      }
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
            {copy.sectionLabel}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-cyber-neon">{copy.pageTitle}</h1>
            {isPerso ? <PersoTag /> : null}
          </div>
          <p className="mt-1 max-w-xl text-sm text-cyber-muted">{copy.subtitle}</p>
        </div>
        <button type="button" className="cyber-action-btn" onClick={startNew}>
          {copy.newButton}
        </button>
      </header>

      {error ? (
        <section className="cyber-panel border-red-400/30 p-4">
          <pre className="whitespace-pre-wrap text-xs text-red-300">{error}</pre>
        </section>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(220px,280px)_1fr]">
        <aside className="cyber-panel p-3">
          <p className="mb-2 text-[10px] uppercase tracking-wider text-cyber-muted">
            {copy.listLabel} ({clients.length})
          </p>
          {loading ? (
            <p className="text-xs text-cyber-muted animate-pulse">Chargement…</p>
          ) : clients.length === 0 ? (
            <p className="text-xs text-cyber-muted">{copy.emptyList}</p>
          ) : (
            <ul className="space-y-1">
              {clients.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => selectClient(c.id)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                      selectedId === c.id && !isNew
                        ? "bg-cyber-violet/20 text-cyber-neon"
                        : "text-cyber-muted hover:bg-white/5 hover:text-cyber-text"
                    }`}
                  >
                    <span className="flex flex-wrap items-center gap-1.5">
                      <span className="font-medium">{c.name}</span>
                      {isPerso ? <PersoTag /> : null}
                    </span>
                    {c.company ? (
                      <span className="mt-0.5 block text-[11px] opacity-70">
                        {c.company}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="cyber-panel p-5">
          {!selectedId && !isNew ? (
            <p className="text-sm text-cyber-muted">{copy.selectHint}</p>
          ) : (
            <form onSubmit={(e) => void handleSave(e)} className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-semibold text-cyber-neon">
                    {isNew ? copy.formNew : copy.formEdit}
                  </h2>
                  {isPerso && !isNew ? <PersoTag /> : null}
                  {isNew && isPerso ? <PersoTag /> : null}
                </div>
                {!isNew && detail ? (
                  <p className="text-[11px] text-cyber-muted">
                    Créé le {formatDate(detail.created_at)}
                  </p>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block space-y-1 sm:col-span-2">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Nom *
                  </span>
                  <input
                    className="cyber-prompt-field w-full"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder={
                      isPerso ? "Nom du projet ou de la démo" : undefined
                    }
                    required
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    {copy.companyLabel}
                  </span>
                  <input
                    className="cyber-prompt-field w-full"
                    value={form.company}
                    onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                    placeholder={copy.companyPlaceholder}
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Email
                  </span>
                  <input
                    type="email"
                    className="cyber-prompt-field w-full"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Téléphone
                  </span>
                  <input
                    className="cyber-prompt-field w-full"
                    value={form.phone}
                    onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Couleur principale
                  </span>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      className="h-10 w-12 cursor-pointer rounded border border-cyber-border bg-transparent"
                      value={form.primary_color || (isPerso ? "#22d3ee" : "#6366f1")}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, primary_color: e.target.value }))
                      }
                    />
                    <input
                      className="cyber-prompt-field min-w-0 flex-1 font-mono text-sm"
                      value={form.primary_color}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, primary_color: e.target.value }))
                      }
                    />
                  </div>
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Logo
                  </span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="text-xs text-cyber-muted"
                    onChange={(e) => handleLogoFile(e.target.files?.[0] ?? null)}
                  />
                  {form.logo_url ? (
                    <img
                      src={form.logo_url}
                      alt="Logo"
                      className="mt-2 h-12 w-12 rounded-lg object-cover"
                    />
                  ) : null}
                </label>
              </div>

              <div className="flex flex-wrap gap-2">
                <button type="submit" className="cyber-generate-btn" disabled={saving}>
                  {saving ? "Enregistrement…" : "Enregistrer"}
                </button>
                {!isNew && selectedId ? (
                  <>
                    <button
                      type="button"
                      className="cyber-action-btn"
                      onClick={() => {
                        if (selectedId) setSelectedClientId(selectedId);
                        onOpenGenerator?.();
                      }}
                    >
                      Créer une démo
                    </button>
                    <button
                      type="button"
                      className="cyber-action-btn border-red-400/40 text-red-300"
                      onClick={() => void handleDelete()}
                      disabled={saving}
                    >
                      Supprimer
                    </button>
                  </>
                ) : null}
              </div>

              {!isNew && detail ? (
                <div className="border-t border-cyber-border pt-6">
                  <h3 className="mb-3 text-sm font-semibold text-cyber-neon">
                    {copy.demosHeading} ({detail.demos.length})
                  </h3>
                  {detailLoading ? (
                    <p className="text-xs text-cyber-muted animate-pulse">Chargement…</p>
                  ) : detail.demos.length === 0 ? (
                    <p className="text-xs text-cyber-muted">{copy.demosEmpty}</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[520px] text-left text-xs">
                        <thead>
                          <tr className="border-b border-cyber-border text-cyber-muted">
                            <th className="py-2 pr-3 font-medium">Titre</th>
                            <th className="py-2 pr-3 font-medium">Statut</th>
                            <th className="py-2 pr-3 font-medium">Envoyée</th>
                            <th className="py-2 pr-3 font-medium">Ouverte</th>
                            <th className="py-2 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detail.demos.map((demo) => (
                            <tr
                              key={demo.id}
                              className="border-b border-cyber-border/50"
                            >
                              <td className="py-2 pr-3 text-cyber-text">
                                {demo.title}
                                {demo.unlock_url ? (
                                  <a
                                    href={demo.unlock_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-0.5 block text-[10px] text-cyber-accent"
                                  >
                                    Lien démo
                                  </a>
                                ) : null}
                              </td>
                              <td className="py-2 pr-3">
                                <span
                                  className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLES[demo.status]}`}
                                >
                                  {DEMO_STATUS_LABELS[demo.status]}
                                </span>
                              </td>
                              <td className="py-2 pr-3 text-cyber-muted">
                                {formatDate(demo.created_at)}
                              </td>
                              <td className="py-2 pr-3 text-cyber-muted">
                                {demo.opened_at
                                  ? formatDate(demo.opened_at)
                                  : "—"}
                              </td>
                              <td className="py-2">
                                <div className="flex flex-wrap gap-1">
                                  {demo.status !== "validee" ? (
                                    <button
                                      type="button"
                                      className="cyber-action-btn !px-2 !py-1 text-[10px]"
                                      onClick={() =>
                                        void handleDemoStatus(demo.id, "validee")
                                      }
                                    >
                                      Validée
                                    </button>
                                  ) : null}
                                  {demo.status !== "expiree" ? (
                                    <button
                                      type="button"
                                      className="cyber-action-btn !px-2 !py-1 text-[10px]"
                                      onClick={() =>
                                        void handleDemoStatus(demo.id, "expiree")
                                      }
                                    >
                                      Expirée
                                    </button>
                                  ) : null}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : null}
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
