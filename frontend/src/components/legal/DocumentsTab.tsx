import { useCallback, useEffect, useState } from "react";
import type { ProjectRecord } from "@shared/types";
import { DocumentFormModal, type DocumentFormValues } from "@/components/legal/DocumentFormModal";
import {
  DOCUMENT_STATUS_OPTIONS,
  StatusBadge,
} from "@/components/legal/StatusBadge";

const STATUS_LABELS: Record<DocumentStatus, string> = {
  draft: "Brouillon",
  sent: "Envoyé",
  signed: "Signé",
  paid: "Payé",
  cancelled: "Annulé",
};
import { apiErrorMessage } from "@/lib/api-errors";
import {
  convertDevisToFacture,
  createDocumentFromProject,
  createLegalDocument,
  deleteLegalDocument,
  fetchLegalClients,
  fetchLegalDocuments,
  fetchProjectsForLegal,
  generateDocumentPdf,
  openPdfDownload,
  sendLegalDocument,
  updateDocumentStatus,
  updateLegalDocument,
  type DocumentStatus,
  type LegalClient,
  type LegalDocument,
} from "@/lib/legal-api";

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", { dateStyle: "short" }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

function clientName(clients: LegalClient[], id: string | null): string {
  if (!id) return "—";
  return clients.find((c) => c.id === id)?.name ?? "—";
}

export function DocumentsTab({
  docType,
  docTypeLabel,
  enableConvertFromSignedDevis,
}: {
  docType: "devis" | "facture";
  docTypeLabel: string;
  /** Onglet Factures : conversion depuis un devis signé */
  enableConvertFromSignedDevis?: boolean;
}) {
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [clients, setClients] = useState<LegalClient[]>([]);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editDoc, setEditDoc] = useState<LegalDocument | null>(null);
  const [formBusy, setFormBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [projectBusy, setProjectBusy] = useState(false);

  const [sendDoc, setSendDoc] = useState<LegalDocument | null>(null);
  const [sendMessage, setSendMessage] = useState(
    "Veuillez trouver ci-joint notre proposition commerciale. N'hésitez pas à nous contacter pour toute question.",
  );
  const [sendBusy, setSendBusy] = useState(false);

  const [statusDoc, setStatusDoc] = useState<LegalDocument | null>(null);
  const [newStatus, setNewStatus] = useState<DocumentStatus>("draft");

  const [signedDevisPickerOpen, setSignedDevisPickerOpen] = useState(false);
  const [signedDevisList, setSignedDevisList] = useState<LegalDocument[]>([]);
  const [selectedSignedDevisId, setSelectedSignedDevisId] = useState("");
  const [convertBusy, setConvertBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [docsRes, clientsRes] = await Promise.all([
      fetchLegalDocuments({ type: docType }),
      fetchLegalClients(),
    ]);
    if (!docsRes.ok) {
      setError(apiErrorMessage(docsRes, "Impossible de charger les documents."));
      setLoading(false);
      return;
    }
    if (!clientsRes.ok) {
      setError(apiErrorMessage(clientsRes, "Impossible de charger les clients."));
      setLoading(false);
      return;
    }
    setDocuments(Array.isArray(docsRes.data) ? docsRes.data : []);
    setClients(Array.isArray(clientsRes.data) ? clientsRes.data : []);
    setLoading(false);
  }, [docType]);

  useEffect(() => {
    void load();
  }, [load]);

  async function loadProjects() {
    const res = await fetchProjectsForLegal();
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
    }
  }

  async function handleFormSubmit(values: DocumentFormValues) {
    setFormBusy(true);
    setFormError(null);
    if (editDoc) {
      const res = await updateLegalDocument(editDoc.id, {
        title: values.title,
        client_id: values.client_id,
        notes: values.notes || null,
        line_items: values.lines,
      });
      if (!res.ok) {
        setFormError(apiErrorMessage(res, "Échec de la mise à jour."));
        setFormBusy(false);
        return;
      }
    } else {
      const res = await createLegalDocument({
        type: docType,
        title: values.title,
        client_id: values.client_id,
        notes: values.notes || null,
        tva_rate: 0,
        line_items: values.lines,
      });
      if (!res.ok) {
        setFormError(apiErrorMessage(res, "Échec de la création."));
        setFormBusy(false);
        return;
      }
    }
    setFormBusy(false);
    setFormOpen(false);
    setEditDoc(null);
    await load();
  }

  async function runAction(id: string, fn: () => Promise<void>) {
    setBusyId(id);
    setActionError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action échouée.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleFromProject() {
    if (!selectedProjectId) return;
    setProjectBusy(true);
    setActionError(null);
    const res = await createDocumentFromProject(selectedProjectId);
    setProjectBusy(false);
    if (!res.ok) {
      setActionError(
        apiErrorMessage(res, "Impossible de créer le devis depuis le projet."),
      );
      return;
    }
    setProjectPickerOpen(false);
    setSelectedProjectId("");
    if (res.data) {
      setEditDoc(res.data);
      setFormOpen(true);
    }
    await load();
  }

  async function handleSend() {
    if (!sendDoc) return;
    setSendBusy(true);
    setActionError(null);
    const res = await sendLegalDocument(sendDoc.id, { message: sendMessage });
    setSendBusy(false);
    if (!res.ok) {
      setActionError(apiErrorMessage(res, "Envoi email impossible."));
      return;
    }
    setSendDoc(null);
    await load();
  }

  async function handleStatusSave() {
    if (!statusDoc) return;
    setBusyId(statusDoc.id);
    const res = await updateDocumentStatus(statusDoc.id, newStatus);
    setBusyId(null);
    if (!res.ok) {
      setActionError(apiErrorMessage(res, "Changement de statut impossible."));
      return;
    }
    setStatusDoc(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary text-xs"
          onClick={() => {
            setEditDoc(null);
            setFormError(null);
            setFormOpen(true);
          }}
        >
          Nouveau {docTypeLabel.toLowerCase()}
        </button>
        {docType === "devis" ? (
          <button
            type="button"
            className="cyber-action-btn text-xs"
            onClick={() => {
              void loadProjects();
              setProjectPickerOpen(true);
            }}
          >
            Depuis un projet
          </button>
        ) : null}
        {enableConvertFromSignedDevis ? (
          <button
            type="button"
            className="cyber-action-btn text-xs"
            onClick={async () => {
              const res = await fetchLegalDocuments({
                type: "devis",
                status: "signed",
              });
              if (res.ok && Array.isArray(res.data)) {
                setSignedDevisList(res.data);
                setSelectedSignedDevisId(res.data[0]?.id ?? "");
              }
              setSignedDevisPickerOpen(true);
            }}
          >
            Convertir depuis devis signé
          </button>
        ) : null}
        <button
          type="button"
          className="cyber-action-btn text-xs"
          onClick={() => void load()}
        >
          Actualiser
        </button>
      </div>

      {error ? (
        <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {actionError ? (
        <p className="rounded border border-amber-500/40 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
          {actionError}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-cyber-muted animate-pulse">Chargement…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-cyber-border">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-cyber-border bg-cyber-surface/80 text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
                <th className="px-3 py-2">Numéro</th>
                <th className="px-3 py-2">Client</th>
                <th className="px-3 py-2">Titre</th>
                <th className="px-3 py-2 text-right">TTC</th>
                <th className="px-3 py-2">Statut</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-cyber-muted">
                    Aucun {docTypeLabel.toLowerCase()} pour le moment.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                  >
                    <td className="px-3 py-2 font-mono text-xs text-cyber-neon">
                      {doc.number}
                    </td>
                    <td className="px-3 py-2 text-cyber-text">
                      {clientName(clients, doc.client_id)}
                    </td>
                    <td className="max-w-[200px] truncate px-3 py-2" title={doc.title}>
                      {doc.title}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">
                      {formatEur(doc.total_ttc)}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-cyber-muted">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        <ActionBtn
                          label="PDF"
                          disabled={busyId === doc.id}
                          onClick={() =>
                            void runAction(doc.id, async () => {
                              const res = await generateDocumentPdf(doc.id);
                              if (!res.ok) {
                                throw new Error(
                                  apiErrorMessage(res, "Génération PDF échouée."),
                                );
                              }
                            })
                          }
                        />
                        <ActionBtn
                          label="↓"
                          title="Télécharger"
                          disabled={!doc.pdf_path && !doc.pdf_url}
                          onClick={() => openPdfDownload(doc)}
                        />
                        <ActionBtn
                          label="✉"
                          title="Envoyer"
                          disabled={!doc.client_id || busyId === doc.id}
                          onClick={() => {
                            setSendDoc(doc);
                            setSendMessage(
                              docType === "devis"
                                ? "Veuillez trouver ci-joint notre devis. Nous restons à votre disposition."
                                : "Veuillez trouver ci-joint votre facture. Merci pour votre confiance.",
                            );
                          }}
                        />
                        <ActionBtn
                          label="◎"
                          title="Statut"
                          onClick={() => {
                            setStatusDoc(doc);
                            setNewStatus(doc.status);
                          }}
                        />
                        <ActionBtn
                          label="✎"
                          title="Modifier"
                          onClick={() => {
                            setEditDoc(doc);
                            setFormError(null);
                            setFormOpen(true);
                          }}
                        />
                        <ActionBtn
                          label="×"
                          title="Supprimer"
                          className="text-red-300"
                          disabled={busyId === doc.id}
                          onClick={() => {
                            if (
                              !window.confirm(
                                `Supprimer ${doc.number} ? Cette action est irréversible.`,
                              )
                            ) {
                              return;
                            }
                            void runAction(doc.id, async () => {
                              const res = await deleteLegalDocument(doc.id);
                              if (!res.ok) {
                                throw new Error(
                                  apiErrorMessage(res, "Suppression impossible."),
                                );
                              }
                            });
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <DocumentFormModal
        open={formOpen}
        mode={editDoc ? "edit" : "create"}
        docTypeLabel={docTypeLabel}
        initial={editDoc}
        clients={clients}
        busy={formBusy}
        error={formError}
        onClientCreated={() => void load()}
        onClose={() => {
          setFormOpen(false);
          setEditDoc(null);
        }}
        onSubmit={handleFormSubmit}
      />

      {projectPickerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="cyber-panel w-full max-w-md border-cyber-violet/40">
            <h3 className="text-base font-semibold text-cyber-text">
              Devis depuis un projet
            </h3>
            <p className="mt-1 text-xs text-cyber-muted">
              Pré-remplit titre, ligne et prix suggéré (P7).
            </p>
            <select
              className="cyber-input mt-4 w-full"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">— Choisir un projet —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn"
                onClick={() => setProjectPickerOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                disabled={!selectedProjectId || projectBusy}
                onClick={() => void handleFromProject()}
              >
                {projectBusy ? "Création…" : "Créer le devis"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {sendDoc ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="cyber-panel w-full max-w-lg border-cyber-neon/30">
            <h3 className="text-base font-semibold text-cyber-text">
              Envoyer {sendDoc.number}
            </h3>
            <p className="mt-1 text-xs text-cyber-muted">
              Email vers {clientName(clients, sendDoc.client_id)}
            </p>
            <textarea
              className="cyber-input mt-3 min-h-[120px] w-full resize-y"
              value={sendMessage}
              onChange={(e) => setSendMessage(e.target.value)}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn"
                onClick={() => setSendDoc(null)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                disabled={sendBusy || !sendMessage.trim()}
                onClick={() => void handleSend()}
              >
                {sendBusy ? "Envoi…" : "Envoyer par mail"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {signedDevisPickerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="cyber-panel w-full max-w-md border-cyber-violet/40">
            <h3 className="text-base font-semibold text-cyber-text">
              Convertir en facture
            </h3>
            <p className="mt-1 text-xs text-cyber-muted">
              Sélectionnez un devis au statut « signé ».
            </p>
            {signedDevisList.length === 0 ? (
              <p className="mt-4 text-sm text-cyber-muted">
                Aucun devis signé disponible.
              </p>
            ) : (
              <select
                className="cyber-input mt-4 w-full"
                value={selectedSignedDevisId}
                onChange={(e) => setSelectedSignedDevisId(e.target.value)}
              >
                {signedDevisList.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.number} — {d.title}
                  </option>
                ))}
              </select>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn"
                onClick={() => setSignedDevisPickerOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                disabled={!selectedSignedDevisId || convertBusy}
                onClick={async () => {
                  const devis = signedDevisList.find(
                    (d) => d.id === selectedSignedDevisId,
                  );
                  if (!devis) return;
                  setConvertBusy(true);
                  const res = await convertDevisToFacture(devis);
                  setConvertBusy(false);
                  if (!res.ok) {
                    setActionError(
                      apiErrorMessage(res, "Conversion impossible."),
                    );
                    return;
                  }
                  setSignedDevisPickerOpen(false);
                  await load();
                }}
              >
                {convertBusy ? "Conversion…" : "Créer la facture"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {statusDoc ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="cyber-panel w-full max-w-sm border-cyber-border">
            <h3 className="text-base font-semibold text-cyber-text">
              Statut — {statusDoc.number}
            </h3>
            <select
              className="cyber-input mt-3 w-full"
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value as DocumentStatus)}
            >
              {DOCUMENT_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn"
                onClick={() => setStatusDoc(null)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                onClick={() => void handleStatusSave()}
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ActionBtn({
  label,
  title,
  disabled,
  className = "",
  onClick,
}: {
  label: string;
  title?: string;
  disabled?: boolean;
  className?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      className={`rounded border border-cyber-border bg-cyber-bg/60 px-1.5 py-0.5 text-[10px] font-bold text-cyber-muted hover:border-cyber-neon hover:text-cyber-neon disabled:opacity-40 ${className}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
