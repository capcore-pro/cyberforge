import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BackButton } from "@/components/BackButton";
import {
  ClientFormModal,
  type ClientFormValues,
} from "@/components/clients/ClientFormModal";
import {
  DocumentFormModal,
  type DocumentFormValues,
} from "@/components/legal/DocumentFormModal";
import { ProjectPreviewThumbnail } from "@/components/ProjectPreviewThumbnail";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  avatarClasses,
  clientInitials,
  formatRelativeDate,
  joinClientName,
  loadClientMeta,
  saveClientMeta,
  splitClientName,
} from "@/lib/client-page-utils";
import {
  DEMO_STATUS_LABELS,
  createClient,
  deleteClient,
  fetchClientDetail,
  listClients,
  updateClient,
  type ClientDetail,
  type ClientDemoRecord,
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
import {
  STATUS_LABELS,
  TYPE_LABELS,
  loadAllUnifiedProjects,
  type UnifiedProject,
} from "@/lib/unified-projects";

interface ClientsPageProps {
  onOpenGenerator?: () => void;
}

type View = "list" | "detail";

const GOLD_BTN =
  "inline-flex items-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-4 py-2 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(212,168,67,0.4)] disabled:opacity-50";
const GLASS_CARD =
  "rounded-card border border-white/10 bg-white/5 shadow-card backdrop-blur-xl transition-all duration-200 hover:scale-[1.01] hover:border-[#d4a843]/50";
const SECTION_GLASS =
  "rounded-card border border-white/10 bg-white/5 p-5 backdrop-blur-xl";
const GHOST_BTN =
  "rounded-control border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-white/70 backdrop-blur-xl transition hover:border-white/30 hover:text-white";

function emptyFormValues(): ClientFormValues {
  return {
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    company: "",
    website: "",
    address: "",
    notes: "",
    active: true,
  };
}

function formFromClient(
  client: ClientRecord,
  meta?: { website: string; notes: string },
): ClientFormValues {
  const { firstName, lastName } = splitClientName(client.name);
  return {
    firstName,
    lastName,
    email: client.email ?? "",
    phone: client.phone ?? "",
    company: client.company ?? "",
    website: meta?.website ?? "",
    address: client.address ?? "",
    notes: meta?.notes ?? "",
    active: client.active !== false,
  };
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

const DEMO_STATUS_CLASS: Record<DemoStatusSlug, string> = {
  envoyee: "text-white/50",
  ouverte: "text-blue-300",
  interessee: "text-amber-300",
  validee: "text-emerald-300",
  expiree: "text-white/40",
};

function ClientAvatar({
  name,
  size = "md",
}: {
  name: string;
  size?: "md" | "lg";
}) {
  const sizeClass =
    size === "lg"
      ? "h-20 w-20 text-2xl"
      : "h-12 w-12 text-sm";
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full border font-semibold ${sizeClass} ${avatarClasses(name)}`}
      aria-hidden
    >
      {clientInitials(name)}
    </div>
  );
}

function ClientCard({
  client,
  projectCount,
  onOpen,
  onNewProject,
  onDelete,
  deleteBusy,
}: {
  client: ClientRecord;
  projectCount: number;
  onOpen: () => void;
  onNewProject: () => void;
  onDelete: () => void;
  deleteBusy: boolean;
}) {
  const active = client.active !== false;

  return (
    <article
      className={`${GLASS_CARD} flex flex-col p-5`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start gap-3">
        <ClientAvatar name={client.name} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate text-base font-semibold text-white">
                {client.name}
              </h3>
              {client.company ? (
                <p className="truncate text-sm text-[#d4a843]/90">
                  {client.company}
                </p>
              ) : null}
            </div>
            <span
              className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                active
                  ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
                  : "border-red-400/35 bg-red-500/15 text-red-300"
              }`}
            >
              {active ? "Actif" : "Inactif"}
            </span>
          </div>

          <dl className="mt-3 space-y-1 text-xs text-white/55">
            <div className="flex gap-2">
              <dt className="shrink-0 text-white/35">Email</dt>
              <dd className="truncate">{client.email || "—"}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="shrink-0 text-white/35">Tél.</dt>
              <dd>{client.phone || "—"}</dd>
            </div>
          </dl>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white/60">
              {projectCount} projet{projectCount !== 1 ? "s" : ""}
            </span>
            <span className="text-[11px] text-white/40">
              {formatRelativeDate(client.created_at)}
            </span>
          </div>
        </div>
      </div>

      <div
        className="mt-4 flex flex-wrap gap-2 border-t border-white/10 pt-4"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <button type="button" onClick={onOpen} className={GHOST_BTN}>
          Voir fiche →
        </button>
        <button type="button" onClick={onNewProject} className={GHOST_BTN}>
          Nouveau projet
        </button>
        <button
          type="button"
          disabled={deleteBusy}
          onClick={onDelete}
          className="rounded-control border border-red-500/30 px-3 py-1.5 text-xs text-red-300 transition hover:border-red-400/50 hover:bg-red-950/30 disabled:opacity-50"
        >
          Supprimer
        </button>
      </div>
    </article>
  );
}

/**
 * Gestion des clients commerciaux — liste premium, fiche détaillée et modal.
 */
export function ClientsPage({ onOpenGenerator }: ClientsPageProps) {
  const { patch } = useGeneratorSession();

  const [view, setView] = useState<View>("list");
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [allProjects, setAllProjects] = useState<UnifiedProject[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [legalClients, setLegalClients] = useState<LegalClient[]>([]);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleteBusyId, setDeleteBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [formInitial, setFormInitial] = useState(emptyFormValues);
  const [formError, setFormError] = useState<string | null>(null);

  const [devisModalOpen, setDevisModalOpen] = useState(false);
  const [factureModalOpen, setFactureModalOpen] = useState(false);
  const [docBusy, setDocBusy] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(true);
  const [clientWebsite, setClientWebsite] = useState("");
  const notesTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selectedClient = useMemo(
    () => clients.find((c) => c.id === selectedId) ?? null,
    [clients, selectedId],
  );

  const projectCountByClient = useMemo(() => {
    const map = new Map<string, number>();
    for (const project of allProjects) {
      if (!project.clientId) continue;
      map.set(project.clientId, (map.get(project.clientId) ?? 0) + 1);
    }
    return map;
  }, [allProjects]);

  const clientProjects = useMemo(() => {
    if (!detail) return [];
    return allProjects.filter((p) => p.clientId === detail.id);
  }, [allProjects, detail]);

  const orphanDemos = useMemo(() => {
    if (!detail) return [];
    const linkedDemoIds = new Set(
      clientProjects.map((p) => p.demoId).filter(Boolean),
    );
    return detail.demos.filter((d) => !linkedDemoIds.has(d.id));
  }, [detail, clientProjects]);

  const devisList = useMemo(
    () => documents.filter((d) => d.type === "devis"),
    [documents],
  );

  const factureList = useMemo(
    () => documents.filter((d) => d.type === "facture"),
    [documents],
  );

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [clientsRes, projects] = await Promise.all([
        listClients("client"),
        loadAllUnifiedProjects(),
      ]);
      if (!clientsRes.ok || !clientsRes.data) {
        setError(
          apiErrorMessage(clientsRes, "Impossible de charger les clients."),
        );
        return;
      }
      setClients(clientsRes.data);
      setAllProjects(projects);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Impossible de charger les clients.",
      );
    } finally {
      setLoading(false);
    }
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

    const meta = loadClientMeta(clientId);
    setNotes(meta.notes);
    setClientWebsite(meta.website);
    setNotesSaved(true);

    if (legalClientsRes.ok && legalClientsRes.data) {
      setLegalClients(legalClientsRes.data);
    }

    const legalId = clientDetail.legal_client_id;
    if (legalId) {
      const docsRes = await fetchLegalDocuments({ client_id: legalId });
      setDocuments(docsRes.ok && docsRes.data ? docsRes.data : []);
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

  useEffect(() => {
    return () => {
      if (notesTimerRef.current) clearTimeout(notesTimerRef.current);
    };
  }, []);

  function openList() {
    setView("list");
    setSelectedId(null);
    setDetail(null);
    setError(null);
  }

  function openNewForm() {
    setFormMode("create");
    setFormInitial(emptyFormValues());
    setFormError(null);
    setFormOpen(true);
  }

  function openEditForm() {
    if (!detail) return;
    const meta = loadClientMeta(detail.id);
    setFormMode("edit");
    setFormInitial(formFromClient(detail, meta));
    setFormError(null);
    setFormOpen(true);
  }

  function openDetail(clientId: string) {
    setSelectedId(clientId);
    setView("detail");
  }

  function startProjectForClient(client: ClientRecord) {
    setSelectedClientId(client.id);
    const label = client.company?.trim() || client.name;
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

  async function handleFormSubmit(values: ClientFormValues) {
    const name = joinClientName(values.firstName, values.lastName);
    if (!name) {
      setFormError("Le prénom et le nom sont obligatoires.");
      return;
    }
    if (!values.email.trim()) {
      setFormError("L'email est obligatoire.");
      return;
    }

    setSaving(true);
    setFormError(null);
    const payload = {
      kind: "client" as const,
      name,
      company: values.company.trim() || null,
      email: values.email.trim() || null,
      phone: values.phone.trim() || null,
      address: values.address.trim() || null,
      active: values.active,
    };

    if (formMode === "create") {
      const response = await createClient(payload);
      setSaving(false);
      if (!response.ok || !response.data) {
        setFormError(apiErrorMessage(response, "Création impossible."));
        return;
      }
      saveClientMeta(response.data.id, {
        website: values.website.trim(),
        notes: values.notes.trim(),
      });
      setFormOpen(false);
      await loadClients();
      openDetail(response.data.id);
      return;
    }

    if (!selectedId) return;
    const response = await updateClient(selectedId, payload);
    setSaving(false);
    if (!response.ok) {
      setFormError(apiErrorMessage(response, "Enregistrement impossible."));
      return;
    }
    saveClientMeta(selectedId, {
      website: values.website.trim(),
      notes: values.notes.trim(),
    });
    setFormOpen(false);
    setNotes(values.notes.trim());
    setClientWebsite(values.website.trim());
    await loadClients();
    void loadDetail(selectedId);
  }

  async function handleDeleteClient(client: ClientRecord) {
    const confirmed = window.confirm(
      `Supprimer le client « ${client.name} » ? Cette action est irréversible.`,
    );
    if (!confirmed) return;

    setDeleteBusyId(client.id);
    setError(null);
    const response = await deleteClient(client.id);
    setDeleteBusyId(null);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Suppression impossible."));
      return;
    }
    if (selectedId === client.id) openList();
    await loadClients();
  }

  function handleNotesChange(value: string) {
    setNotes(value);
    setNotesSaved(false);
    if (!selectedId) return;
    if (notesTimerRef.current) clearTimeout(notesTimerRef.current);
    notesTimerRef.current = setTimeout(() => {
      const meta = loadClientMeta(selectedId);
      saveClientMeta(selectedId, { ...meta, notes: value });
      setNotesSaved(true);
    }, 600);
  }

  async function handleCreateDocument(
    type: "devis" | "facture",
    values: DocumentFormValues,
  ) {
    if (!detail?.legal_client_id) {
      setDocError("Fiche légale non liée — enregistrez à nouveau le client.");
      return;
    }
    setDocBusy(true);
    setDocError(null);
    const res = await createLegalDocument({
      type,
      title: values.title,
      client_id: detail.legal_client_id,
      notes: values.notes || null,
      line_items: values.lines,
    });
    setDocBusy(false);
    if (!res.ok) {
      setDocError(
        apiErrorMessage(
          res,
          type === "devis"
            ? "Création du devis impossible."
            : "Création de la facture impossible.",
        ),
      );
      return;
    }
    if (type === "devis") setDevisModalOpen(false);
    else setFactureModalOpen(false);
    void loadDetail(detail.id);
  }

  const legalDocInitial = useCallback(
    (type: "devis" | "facture"): LegalDocument | null => {
      if (!detail?.legal_client_id) return null;
      const label = detail.company?.trim() || detail.name;
      const prefix = type === "devis" ? "Devis" : "Facture";
      return {
        id: "",
        type,
        number: "",
        client_id: detail.legal_client_id,
        project_id: null,
        status: "draft",
        title: `${prefix} — ${label}`,
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
    },
    [detail],
  );

  function renderDemoRow(demo: ClientDemoRecord) {
    return (
      <li
        key={demo.id}
        className="flex flex-wrap items-center gap-3 rounded-control border border-white/10 bg-white/5 px-3 py-3"
      >
        <div className="h-14 w-24 shrink-0 overflow-hidden rounded-md border border-white/10 bg-black/40">
          <div className="flex h-full items-center justify-center text-[10px] text-white/30">
            Démo
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white">{demo.title}</p>
          <p className="text-[11px] text-white/45">
            Démo ·{" "}
            <span className={DEMO_STATUS_CLASS[demo.status]}>
              {DEMO_STATUS_LABELS[demo.status]}
            </span>{" "}
            · {formatRelativeDate(demo.created_at)}
          </p>
        </div>
        {demo.unlock_url ? (
          <a
            href={demo.unlock_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-[#d4a843] hover:underline"
          >
            Voir démo ↗
          </a>
        ) : null}
      </li>
    );
  }

  function renderProjectRow(project: UnifiedProject) {
    return (
      <li
        key={project.key}
        className="flex flex-wrap items-center gap-3 rounded-control border border-white/10 bg-white/5 px-3 py-3"
      >
        <div className="h-14 w-24 shrink-0 overflow-hidden rounded-md border border-white/10">
          <ProjectPreviewThumbnail
            previewUrl={project.url}
            title={project.name}
            width={96}
            height={56}
            className="h-full w-full"
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white">{project.name}</p>
          <p className="text-[11px] text-white/45">
            {TYPE_LABELS[project.type]} · {STATUS_LABELS[project.status]} ·{" "}
            {formatRelativeDate(project.createdAt)}
          </p>
        </div>
        {project.url ? (
          <a
            href={project.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-[#d4a843] hover:underline"
          >
            Voir démo ↗
          </a>
        ) : null}
      </li>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {view === "list" ? (
        <>
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
                Relation client
              </p>
              <h1 className="text-2xl font-semibold text-white">Clients</h1>
              <p className="mt-1 text-sm text-white/50">
                Fiches clients, projets, devis et factures
              </p>
            </div>
            <button type="button" onClick={openNewForm} className={GOLD_BTN}>
              <span aria-hidden>+</span>
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
                  className="h-48 animate-pulse rounded-card border border-white/10 bg-white/5 backdrop-blur-xl"
                />
              ))}
            </div>
          ) : clients.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-card border border-white/10 bg-white/5 px-6 py-16 text-center backdrop-blur-xl">
              <span
                className="mb-4 inline-block animate-pulse text-5xl"
                aria-hidden
              >
                👥
              </span>
              <h2 className="text-lg font-semibold text-white">
                Aucun client pour le moment
              </h2>
              <p className="mt-2 max-w-sm text-sm text-white/50">
                Ajoutez votre premier client pour commencer
              </p>
              <button
                type="button"
                onClick={openNewForm}
                className={`${GOLD_BTN} mt-6`}
              >
                ＋ Ajouter mon premier client
              </button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {clients.map((client) => (
                <ClientCard
                  key={client.id}
                  client={client}
                  projectCount={projectCountByClient.get(client.id) ?? 0}
                  onOpen={() => openDetail(client.id)}
                  onNewProject={() => startProjectForClient(client)}
                  onDelete={() => void handleDeleteClient(client)}
                  deleteBusy={deleteBusyId === client.id}
                />
              ))}
            </div>
          )}
        </>
      ) : null}

      {view === "detail" && selectedClient ? (
        <section className="space-y-6">
          <BackButton className="mb-2" onClick={openList} />

          <div className={`${SECTION_GLASS} p-6`}>
            <div className="flex flex-wrap items-start gap-5">
              <ClientAvatar name={selectedClient.name} size="lg" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-2xl font-semibold text-white">
                    {selectedClient.name}
                  </h2>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                      selectedClient.active !== false
                        ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
                        : "border-red-400/35 bg-red-500/15 text-red-300"
                    }`}
                  >
                    {selectedClient.active !== false ? "Actif" : "Inactif"}
                  </span>
                </div>
                {selectedClient.company ? (
                  <p className="mt-1 text-sm text-[#d4a843]/90">
                    {selectedClient.company}
                  </p>
                ) : null}
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-white/35">
                      Email
                    </dt>
                    <dd className="text-white/80">
                      {selectedClient.email || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-white/35">
                      Téléphone
                    </dt>
                    <dd className="text-white/80">
                      {selectedClient.phone || "—"}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs uppercase tracking-wide text-white/35">
                      Adresse
                    </dt>
                    <dd className="text-white/80">
                      {selectedClient.address || "—"}
                    </dd>
                  </div>
                  {clientWebsite ? (
                    <div className="sm:col-span-2">
                      <dt className="text-xs uppercase tracking-wide text-white/35">
                        Site web
                      </dt>
                      <dd>
                        <a
                          href={clientWebsite}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#d4a843] hover:underline"
                        >
                          {clientWebsite}
                        </a>
                      </dd>
                    </div>
                  ) : null}
                </dl>
              </div>

              <div className="flex w-full flex-wrap gap-2 lg:w-auto lg:flex-col lg:items-stretch">
                <button
                  type="button"
                  onClick={() => startProjectForClient(selectedClient)}
                  className={GOLD_BTN}
                >
                  ⚡ Créer un projet
                </button>
                <button type="button" onClick={openEditForm} className={GHOST_BTN}>
                  Modifier
                </button>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void handleDeleteClient(selectedClient)}
                  className="rounded-control border border-red-500/30 px-3 py-2 text-xs text-red-300 hover:bg-red-950/30"
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
            <p className="animate-pulse text-sm text-white/50">Chargement…</p>
          ) : (
            <>
              <div className={SECTION_GLASS}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
                    Projets
                  </h3>
                  <button
                    type="button"
                    onClick={() => startProjectForClient(selectedClient)}
                    className={GHOST_BTN}
                  >
                    Nouveau projet
                  </button>
                </div>
                {!clientProjects.length && !orphanDemos.length ? (
                  <button
                    type="button"
                    onClick={() => startProjectForClient(selectedClient)}
                    className="text-sm text-[#d4a843] hover:underline"
                  >
                    Aucun projet — créer le premier ↗
                  </button>
                ) : (
                  <ul className="space-y-2">
                    {clientProjects.map(renderProjectRow)}
                    {orphanDemos.map(renderDemoRow)}
                  </ul>
                )}
              </div>

              <div className={SECTION_GLASS}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
                    Devis
                  </h3>
                  <button
                    type="button"
                    onClick={() => setDevisModalOpen(true)}
                    disabled={!detail?.legal_client_id}
                    className={GHOST_BTN}
                  >
                    Créer un devis
                  </button>
                </div>
                {!devisList.length ? (
                  <p className="text-sm text-white/45">
                    Aucun devis pour ce client.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {devisList.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-white/10 bg-white/5 px-3 py-2.5"
                      >
                        <div>
                          <p className="text-sm text-white">{doc.title}</p>
                          <p className="text-[11px] text-white/45">
                            {doc.number} · {formatRelativeDate(doc.created_at)}
                          </p>
                        </div>
                        <div className="text-right text-xs">
                          <p className="font-medium text-[#d4a843]">
                            {formatEur(doc.total_ttc)}
                          </p>
                          <p className="capitalize text-white/40">{doc.status}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={SECTION_GLASS}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
                    Factures
                  </h3>
                  <button
                    type="button"
                    onClick={() => setFactureModalOpen(true)}
                    disabled={!detail?.legal_client_id}
                    className={GHOST_BTN}
                  >
                    Créer une facture
                  </button>
                </div>
                {!factureList.length ? (
                  <p className="text-sm text-white/45">
                    Aucune facture pour ce client.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {factureList.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-white/10 bg-white/5 px-3 py-2.5"
                      >
                        <div>
                          <p className="text-sm text-white">{doc.title}</p>
                          <p className="text-[11px] text-white/45">
                            {doc.number} · {formatRelativeDate(doc.created_at)}
                          </p>
                        </div>
                        <div className="text-right text-xs">
                          <p className="font-medium text-[#d4a843]">
                            {formatEur(doc.total_ttc)}
                          </p>
                          <p className="capitalize text-white/40">{doc.status}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={SECTION_GLASS}>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
                    Notes internes
                  </h3>
                  <span className="text-[11px] text-white/35">
                    {notesSaved ? "Sauvegardé" : "Enregistrement…"}
                  </span>
                </div>
                <textarea
                  rows={5}
                  value={notes}
                  onChange={(e) => handleNotesChange(e.target.value)}
                  placeholder="Notes privées sur ce client…"
                  className="w-full resize-y rounded-control border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none"
                />
              </div>
            </>
          )}
        </section>
      ) : null}

      <ClientFormModal
        open={formOpen}
        title={formMode === "create" ? "Nouveau client" : "Modifier le client"}
        submitLabel={formMode === "create" ? "Créer le client" : "Enregistrer"}
        initial={formInitial}
        busy={saving}
        error={formError}
        onClose={() => {
          setFormOpen(false);
          setFormError(null);
        }}
        onSubmit={(values) => void handleFormSubmit(values)}
      />

      <DocumentFormModal
        open={devisModalOpen}
        mode="create"
        docTypeLabel="Devis"
        initial={legalDocInitial("devis")}
        clients={legalClients}
        onClose={() => {
          setDevisModalOpen(false);
          setDocError(null);
        }}
        onSubmit={(values) => void handleCreateDocument("devis", values)}
        busy={docBusy}
        error={docError}
      />

      <DocumentFormModal
        open={factureModalOpen}
        mode="create"
        docTypeLabel="Facture"
        initial={legalDocInitial("facture")}
        clients={legalClients}
        onClose={() => {
          setFactureModalOpen(false);
          setDocError(null);
        }}
        onSubmit={(values) => void handleCreateDocument("facture", values)}
        busy={docBusy}
        error={docError}
      />
    </div>
  );
}
