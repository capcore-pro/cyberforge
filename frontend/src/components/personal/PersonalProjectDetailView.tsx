import { useState } from "react";
import { BackButton } from "@/components/BackButton";
import { PersoBadge } from "@/components/PersoBadge";
import { ProjectDetailView } from "@/components/ProjectDetailView";
import { apiErrorMessage } from "@/lib/api-errors";
import { formatDeletionReport } from "@/lib/deletion-report";
import { listClients, type ClientRecord } from "@/lib/clients-api";
import {
  convertPersonalToClient,
  deletePersonalProject,
  USAGE_LABELS,
  type PersonalProject,
} from "@/lib/personal-projects-api";
import { deleteUnifiedProject, type UnifiedProject } from "@/lib/unified-projects";

function formatEur(n: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

export function PersonalProjectDetailView({
  personal,
  linkedProject,
  onBack,
  onUpdated,
  onView,
}: {
  personal: PersonalProject;
  linkedProject: UnifiedProject | null;
  onBack: () => void;
  onUpdated: (pp: PersonalProject) => void;
  onView: () => void;
}) {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [clientId, setClientId] = useState("");
  const [convertBusy, setConvertBusy] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteReport, setDeleteReport] = useState<string | null>(null);

  const isSale = personal.usage_type === "one_shot" || personal.usage_type === "subscription";

  async function loadClients() {
    const res = await listClients("client");
    if (res.ok && Array.isArray(res.data)) {
      setClients(res.data);
    }
  }

  async function handleConvert() {
    if (!clientId.trim()) {
      setConvertError("Sélectionnez un client.");
      return;
    }
    setConvertBusy(true);
    setConvertError(null);
    const res = await convertPersonalToClient(personal.id, clientId.trim());
    setConvertBusy(false);
    if (!res.ok) {
      setConvertError(apiErrorMessage(res, "Conversion impossible."));
      return;
    }
    onBack();
  }

  async function handleDelete() {
    const msg = linkedProject
      ? `Supprimer « ${personal.title} » ? Cette action est irréversible et effacera le site déployé, le repo GitHub et toutes les données associées.`
      : `Supprimer « ${personal.title} » de la liste perso ?`;
    if (!window.confirm(msg)) return;

    setDeleteBusy(true);
    setConvertError(null);
    setDeleteReport(null);

    let reportText: string | null = null;
    if (linkedProject) {
      const result = await deleteUnifiedProject(linkedProject);
      if (result.report?.items.length) {
        reportText = formatDeletionReport(result.report.items);
      }
      if (!result.ok && !result.report) {
        setConvertError(result.error ?? "Suppression du projet lié impossible.");
        setDeleteBusy(false);
        return;
      }
    }

    const res = await deletePersonalProject(personal.id);
    setDeleteBusy(false);
    if (!res.ok) {
      setConvertError(apiErrorMessage(res, "Suppression impossible."));
      return;
    }
    if (reportText) {
      setDeleteReport(reportText);
      return;
    }
    onBack();
  }

  if (linkedProject) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <PersoBadge />
          <span className="text-xs text-cf-muted">{USAGE_LABELS[personal.usage_type]}</span>
        </div>
        <ProjectDetailView
          project={linkedProject}
          onBack={onBack}
          onEdit={() => {}}
          onView={onView}
          onProjectUpdated={() => onUpdated(personal)}
          onDuplicate={() => {}}
          hideClientAffiliate
          extraSections={
            <>
              {isSale ? (
                <CommercializationSection personal={personal} />
              ) : null}
              <ConvertToClientSection
                clients={clients}
                clientId={clientId}
                onClientIdChange={setClientId}
                onLoadClients={() => void loadClients()}
                onConvert={() => void handleConvert()}
                busy={convertBusy}
                error={convertError}
              />
            </>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <BackButton onClick={onBack} />
      <header className="flex flex-wrap items-center gap-2">
        <PersoBadge />
        <h1 className="text-xl font-semibold text-cf-text">{personal.title}</h1>
      </header>

      <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card space-y-3">
        <p className="text-sm text-cf-muted">{USAGE_LABELS[personal.usage_type]}</p>
        {personal.commercial_description ? (
          <p className="text-sm text-cf-text">{personal.commercial_description}</p>
        ) : null}
        {personal.app_type ? (
          <p className="text-xs text-cf-muted">Mini-app : {personal.app_type}</p>
        ) : null}
      </section>

      {isSale ? <CommercializationSection personal={personal} /> : null}

      {deleteReport ? (
        <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
          <h2 className="text-sm font-semibold text-cf-text">Rapport de suppression</h2>
          <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-cf-muted">
            {deleteReport}
          </pre>
          <button
            type="button"
            className="mt-3 text-xs text-cf-gold hover:underline"
            onClick={onBack}
          >
            Retour à la liste
          </button>
        </section>
      ) : null}

      <ConvertToClientSection
        clients={clients}
        clientId={clientId}
        onClientIdChange={setClientId}
        onLoadClients={() => void loadClients()}
        onConvert={() => void handleConvert()}
        busy={convertBusy}
        error={convertError}
      />

      <button
        type="button"
        disabled={deleteBusy}
        onClick={() => void handleDelete()}
        className="rounded-control border border-red-500/40 px-4 py-2 text-xs text-red-300"
      >
        Supprimer de la liste perso
      </button>
    </div>
  );
}

function CommercializationSection({ personal }: { personal: PersonalProject }) {
  return (
    <section className="rounded-card border border-cf-gold/30 bg-cf-active/50 p-5 shadow-card">
      <h2 className="text-sm font-semibold text-cf-gold">Commercialisation</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        {personal.price_eur != null ? (
          <div>
            <dt className="text-[10px] uppercase text-cf-label">Prix</dt>
            <dd className="text-cf-text">
              {formatEur(personal.price_eur)}
              {personal.usage_type === "subscription" ? " / mois" : ""}
            </dd>
          </div>
        ) : null}
        <div>
          <dt className="text-[10px] uppercase text-cf-label">Ventes</dt>
          <dd className="text-cf-text">{personal.sales_count}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase text-cf-label">Revenus</dt>
          <dd className="font-medium text-emerald-400">{formatEur(personal.revenue_eur)}</dd>
        </div>
        {personal.sale_link ? (
          <div className="sm:col-span-2">
            <dt className="text-[10px] uppercase text-cf-label">Lien de vente</dt>
            <dd>
              <a
                href={personal.sale_link}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-cf-info hover:underline"
              >
                {personal.sale_link}
              </a>
            </dd>
          </div>
        ) : null}
        {personal.published_on_capcore ? (
          <div className="sm:col-span-2">
            <span className="rounded border border-cf-gold/40 px-2 py-0.5 text-[10px] text-cf-gold">
              Publié sur capcore.pro
            </span>
          </div>
        ) : null}
      </dl>
    </section>
  );
}

function ConvertToClientSection({
  clients,
  clientId,
  onClientIdChange,
  onLoadClients,
  onConvert,
  busy,
  error,
}: {
  clients: ClientRecord[];
  clientId: string;
  onClientIdChange: (id: string) => void;
  onLoadClients: () => void;
  onConvert: () => void;
  busy: boolean;
  error: string | null;
}) {
  return (
    <section className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
      <h2 className="text-sm font-semibold text-cf-text">Basculer en projet client</h2>
      <p className="mt-1 text-xs text-cf-muted">
        Réaffecte le projet à un client commercial et le retire de la liste perso.
      </p>
      <select
        value={clientId}
        onFocus={onLoadClients}
        onChange={(e) => onClientIdChange(e.target.value)}
        className="mt-3 w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm"
      >
        <option value="">— Choisir un client —</option>
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {c.company?.trim() || c.name}
          </option>
        ))}
      </select>
      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
      <button
        type="button"
        disabled={busy || !clientId}
        onClick={onConvert}
        className="mt-3 rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-xs text-cf-gold disabled:opacity-50"
      >
        {busy ? "Conversion…" : "Basculer en projet client"}
      </button>
    </section>
  );
}
