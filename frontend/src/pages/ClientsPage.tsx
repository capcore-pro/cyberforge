import { useCallback, useEffect, useMemo, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import {
  DocumentFormModal,
  type DocumentFormValues,
} from "@/components/legal/DocumentFormModal";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  DEMO_STATUS_LABELS,
  createClient,
  deleteClient,
  fetchClientDetail,
  listClients,
  updateClient,
  type ClientDetail,
  type ClientRecord,
  type DemoStatusSlug,
} from "@/lib/clients-api";
import {
  createLegalDocument,
  fetchLegalClients,
  fetchLegalDocuments,
  type LegalClient,
  type LegalDocument,
} from "@/lib/legal-api";
import { setSelectedClientId } from "@/lib/selected-client";

interface ClientsPageProps {
  onOpenGenerator?: () => void;
}

type View = "list" | "form" | "detail";

interface ClientFormState {
  name: string;
  company: string;
  email: string;
  phone: string;
  address: string;
  siret: string;
  active: boolean;
}

function emptyForm(): ClientFormState {
  return {
    name: "",
    company: "",
    email: "",
    phone: "",
    address: "",
    siret: "",
    active: true,
  };
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

const DEMO_STATUS_CLASS: Record<DemoStatusSlug, string> = {
  envoyee: "text-cf-muted",
  ouverte: "text-cf-info",
  interessee: "text-cf-alert",
  validee: "text-cf-success",
  expiree: "text-cf-muted",
};

function ClientCard({
  client,
  onClick,
}: {
  client: ClientRecord;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full flex-col rounded-card border border-cf-border-input bg-cf-card p-4 text-left shadow-card transition hover:border-cf-gold/40"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-cf-text">{client.name}</h3>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase ${
            client.active !== false
              ? "border-cf-success/40 bg-cf-success/10 text-cf-success"
              : "border-red-500/40 bg-red-950/30 text-red-300"
          }`}
        >
          {client.active !== false ? "Actif" : "Inactif"}
        </span>
      </div>
      {client.company ? (
        <p className="mt-1 text-xs text-cf-gold">{client.company}</p>
      ) : null}
      <dl className="mt-3 space-y-1 text-xs text-cf-muted">
        <div className="flex gap-2">
          <dt className="text-cf-label">Email</dt>
          <dd className="truncate text-cf-body">{client.email || "—"}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-cf-label">Tél.</dt>
          <dd>{client.phone || "—"}</dd>
        </div>
      </dl>
    </button>
  );
}

/**
 * Gestion des clients commerciaux — liste, fiche et formulaire inline.
 */
export function ClientsPage({ onOpenGenerator }: ClientsPageProps) {
  const { patch } = useGeneratorSession();

  const [view, setView] = useState<View>("list");
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [legalClients, setLegalClients] = useState<LegalClient[]>([]);

  const [form, setForm] = useState<ClientFormState>(emptyForm);
  const [isNew, setIsNew] = useState(false);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [devisModalOpen, setDevisModalOpen] = useState(false);
  const [devisBusy, setDevisBusy] = useState(false);
  const [devisError, setDevisError] = useState<string | null>(null);

  const selectedClient = useMemo(
    () => clients.find((c) => c.id === selectedId) ?? null,
    [clients, selectedId],
  );

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await listClients("client");
    setLoading(false);
    if (!response.ok || !response.data) {
      setError(apiErrorMessage(response, "Impossible de charger les clients."));
      return;
    }
    setClients(response.data);
  }, []);

  const loadDetail = useCallback(async (clientId: string) => {
    setDetailLoading(true);
    setError(null);
    const [detailRes, legalClientsRes] = await Promise.all([
      fetchClientDetail(clientId),
      fetchLegalClients(),
    ]);
    setDetailLoading(false);

    if (!detailRes.ok || !detailRes.data) {
      setError(apiErrorMessage(detailRes, "Impossible de charger la fiche."));
      return;
    }

    const clientDetail = detailRes.data;
    setDetail(clientDetail);

    if (legalClientsRes.ok && legalClientsRes.data) {
      setLegalClients(legalClientsRes.data);
    }

    const legalId = clientDetail.legal_client_id;
    if (legalId) {
      const docsRes = await fetchLegalDocuments({ client_id: legalId });
      if (docsRes.ok && docsRes.data) {
        setDocuments(docsRes.data);
      } else {
        setDocuments([]);
      }
    } else {
      setDocuments([]);
    }
  }, []);

  useEffect(() => {
    void loadClients();
  }, [loadClients]);

  useEffect(() => {
    if (view === "detail" && selectedId) {
      void loadDetail(selectedId);
    }
  }, [view, selectedId, loadDetail]);

  function openList() {
    setView("list");
    setSelectedId(null);
    setDetail(null);
    setIsNew(false);
    setError(null);
  }

  function openNewForm() {
    setIsNew(true);
    setSelectedId(null);
    setDetail(null);
    setForm(emptyForm());
    setError(null);
    setView("form");
  }

  function openDetail(clientId: string) {
    setSelectedId(clientId);
    setIsNew(false);
    setView("detail");
  }

  function openEditForm() {
    if (!detail) return;
    setForm({
      name: detail.name,
      company: detail.company ?? "",
      email: detail.email ?? "",
      phone: detail.phone ?? "",
      address: detail.address ?? "",
      siret: detail.siret ?? "",
      active: detail.active !== false,
    });
    setIsNew(false);
    setView("form");
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
      kind: "client" as const,
      name,
      company: form.company.trim() || null,
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      siret: form.siret.trim() || null,
      active: form.active,
    };

    if (isNew) {
      const response = await createClient(payload);
      setSaving(false);
      if (!response.ok || !response.data) {
        setError(apiErrorMessage(response, "Création impossible."));
        return;
      }
      await loadClients();
      openDetail(response.data.id);
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
    setView("detail");
    void loadDetail(selectedId);
  }

  async function handleDelete() {
    if (!selectedId || !detail) return;
    const confirmed = window.confirm(
      `Supprimer le client « ${detail.name} » ? Cette action est irréversible.`,
    );
    if (!confirmed) return;

    setSaving(true);
    const response = await deleteClient(selectedId);
    setSaving(false);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Suppression impossible."));
      return;
    }
    await loadClients();
    openList();
  }

  function handleGenerateProject() {
    if (!detail) return;
    setSelectedClientId(detail.id);
    const company = detail.company?.trim();
    const label = company || detail.name;
    patch({
      prompt: `Projet pour ${label} — site professionnel adapté à leur activité.`,
      projectType: "site_web",
      generationMode: "client_demo",
      phase: "idle",
      error: null,
      actionError: null,
      result: null,
    });
    onOpenGenerator?.();
  }

  async function handleCreateDevis(values: DocumentFormValues) {
    if (!detail?.legal_client_id) {
      setDevisError("Fiche légale non liée — enregistrez à nouveau le client.");
      return;
    }
    setDevisBusy(true);
    setDevisError(null);
    const res = await createLegalDocument({
      type: "devis",
      title: values.title,
      client_id: detail.legal_client_id,
      notes: values.notes || null,
      line_items: values.lines,
    });
    setDevisBusy(false);
    if (!res.ok) {
      setDevisError(apiErrorMessage(res, "Création du devis impossible."));
      return;
    }
    setDevisModalOpen(false);
    void loadDetail(detail.id);
  }

  const devisInitial = useMemo((): LegalDocument | null => {
    if (!detail?.legal_client_id) return null;
    const label = detail.company?.trim() || detail.name;
    return {
      id: "",
      type: "devis",
      number: "",
      client_id: detail.legal_client_id,
      project_id: null,
      status: "draft",
      title: `Devis — ${label}`,
      notes: null,
      total_ht: 0,
      tva_rate: 0,
      total_ttc: 0,
      pdf_path: null,
      pdf_url: null,
      sent_at: null,
      created_at: "",
      line_items: [],
    };
  }, [detail]);

  const devisAndFactures = documents.filter(
    (d) => d.type === "devis" || d.type === "facture",
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {view === "list" ? (
        <>
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="cf-section-label mb-2">Relation client</p>
              <h1 className="cf-page-title">Clients</h1>
              <p className="mt-1 text-sm text-cf-muted">
                Fiches clients, projets, devis et factures
              </p>
            </div>
            <button
              type="button"
              onClick={openNewForm}
              className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm font-medium text-cf-gold hover:border-cf-gold"
            >
              Nouveau client
            </button>
          </header>

          {error ? (
            <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-36 animate-pulse rounded-card border border-cf-border-input bg-cf-card"
                />
              ))}
            </div>
          ) : clients.length === 0 ? (
            <div className="rounded-card border border-cf-border-input bg-cf-card px-6 py-12 text-center">
              <p className="text-sm text-cf-muted">Aucun client pour l&apos;instant.</p>
              <button
                type="button"
                onClick={openNewForm}
                className="mt-3 text-sm text-cf-gold hover:underline"
              >
                Créer le premier client
              </button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {clients.map((client) => (
                <ClientCard
                  key={client.id}
                  client={client}
                  onClick={() => openDetail(client.id)}
                />
              ))}
            </div>
          )}
        </>
      ) : null}

      {view === "form" ? (
        <section className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
          <BackButton
            className="mb-4"
            onClick={() => {
              if (isNew) openList();
              else if (selectedId) {
                setView("detail");
              } else openList();
            }}
          />

          <h2 className="mb-6 text-lg font-medium text-cf-text">
            {isNew ? "Nouveau client" : "Modifier le client"}
          </h2>

          <form onSubmit={(e) => void handleSave(e)} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="cf-section-label mb-1 block">Nom *</span>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="cf-section-label mb-1 block">Entreprise</span>
                <input
                  value={form.company}
                  onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="cf-section-label mb-1 block">Email</span>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="cf-section-label mb-1 block">Téléphone</span>
                <input
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="cf-section-label mb-1 block">Adresse</span>
                <input
                  value={form.address}
                  onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="cf-section-label mb-1 block">SIRET (optionnel)</span>
                <input
                  value={form.siret}
                  onChange={(e) => setForm((f) => ({ ...f, siret: e.target.value }))}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
                />
              </label>
              <label className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
                  className="rounded border-cf-border-input"
                />
                <span className="text-sm text-cf-body">Client actif</span>
              </label>
            </div>

            {error ? (
              <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={saving}
              className="rounded-control border border-cf-gold bg-cf-gold px-6 py-2.5 text-sm font-medium text-cf-main hover:bg-cf-gold-hover disabled:opacity-50"
            >
              {saving ? "Enregistrement…" : "Enregistrer"}
            </button>
          </form>
        </section>
      ) : null}

      {view === "detail" && selectedClient ? (
        <section className="space-y-6">
          <BackButton className="mb-4" onClick={openList} />

          <div className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-xl font-medium text-cf-text">{selectedClient.name}</h2>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase ${
                      selectedClient.active !== false
                        ? "border-cf-success/40 bg-cf-success/10 text-cf-success"
                        : "border-red-500/40 bg-red-950/30 text-red-300"
                    }`}
                  >
                    {selectedClient.active !== false ? "Actif" : "Inactif"}
                  </span>
                </div>
                {selectedClient.company ? (
                  <p className="mt-1 text-sm text-cf-gold">{selectedClient.company}</p>
                ) : null}
                <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-cf-label">Email</dt>
                    <dd className="text-cf-body">{selectedClient.email || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-cf-label">Téléphone</dt>
                    <dd className="text-cf-body">{selectedClient.phone || "—"}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-cf-label">Adresse</dt>
                    <dd className="text-cf-body">{selectedClient.address || "—"}</dd>
                  </div>
                  {selectedClient.siret ? (
                    <div>
                      <dt className="text-cf-label">SIRET</dt>
                      <dd className="text-cf-body">{selectedClient.siret}</dd>
                    </div>
                  ) : null}
                </dl>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={openEditForm}
                  className="rounded-control border border-cf-border-input px-3 py-2 text-xs text-cf-muted hover:text-cf-text"
                >
                  Modifier
                </button>
                <button
                  type="button"
                  onClick={() => setDevisModalOpen(true)}
                  disabled={!detail?.legal_client_id}
                  className="rounded-control border border-cf-gold/40 bg-cf-active px-3 py-2 text-xs text-cf-gold disabled:opacity-40"
                >
                  Créer un devis
                </button>
                <button
                  type="button"
                  onClick={handleGenerateProject}
                  className="rounded-control border border-cf-gold/40 bg-cf-active px-3 py-2 text-xs text-cf-gold"
                >
                  Générer un projet
                </button>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void handleDelete()}
                  className="rounded-control border border-red-500/40 px-3 py-2 text-xs text-red-300 hover:bg-red-950/30"
                >
                  Supprimer
                </button>
              </div>
            </div>
          </div>

          {error ? (
            <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          {detailLoading ? (
            <p className="animate-pulse text-sm text-cf-muted">Chargement…</p>
          ) : (
            <>
              <div className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
                <h3 className="cf-section-label mb-4">Projets & démos</h3>
                {!detail?.demos.length ? (
                  <p className="text-sm text-cf-muted">Aucun projet lié pour l&apos;instant.</p>
                ) : (
                  <ul className="space-y-2">
                    {detail.demos.map((demo) => (
                      <li
                        key={demo.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-cf-border-input bg-cf-secondary/40 px-3 py-2.5"
                      >
                        <div>
                          <p className="text-sm text-cf-text">{demo.title}</p>
                          <p className="text-[11px] text-cf-muted">
                            {formatDate(demo.created_at)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs ${DEMO_STATUS_CLASS[demo.status]}`}
                          >
                            {DEMO_STATUS_LABELS[demo.status]}
                          </span>
                          {demo.unlock_url ? (
                            <a
                              href={demo.unlock_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-cf-gold hover:underline"
                            >
                              Voir
                            </a>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
                <h3 className="cf-section-label mb-4">Devis & factures</h3>
                {!devisAndFactures.length ? (
                  <p className="text-sm text-cf-muted">Aucun document pour ce client.</p>
                ) : (
                  <ul className="space-y-2">
                    {devisAndFactures.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-cf-border-input bg-cf-secondary/40 px-3 py-2.5"
                      >
                        <div>
                          <p className="text-sm text-cf-text">
                            {doc.type === "devis" ? "Devis" : "Facture"} — {doc.title}
                          </p>
                          <p className="text-[11px] text-cf-muted">
                            {doc.number} · {formatDate(doc.created_at)}
                          </p>
                        </div>
                        <div className="text-right text-xs">
                          <p className="font-medium text-cf-gold">
                            {formatEur(doc.total_ttc)}
                          </p>
                          <p className="text-cf-muted capitalize">{doc.status}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </section>
      ) : null}

      <DocumentFormModal
        open={devisModalOpen}
        mode="create"
        docTypeLabel="Devis"
        initial={devisInitial}
        clients={legalClients}
        onClose={() => {
          setDevisModalOpen(false);
          setDevisError(null);
        }}
        onSubmit={(values) => void handleCreateDevis(values)}
        busy={devisBusy}
        error={devisError}
      />
    </div>
  );
}
