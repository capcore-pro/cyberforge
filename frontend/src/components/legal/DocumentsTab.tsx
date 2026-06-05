import { useCallback, useEffect, useState } from "react";
import { FileText } from "lucide-react";
import type { ProjectRecord } from "@shared/types";
import {
  GLASS_BTN,
  GLASS_SECTION,
  GOLD_BTN,
  INPUT,
  SELECT,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { AccountingToast } from "@/components/accounting/AccountingToast";
import { BackButton } from "@/components/BackButton";
import { DocumentFormModal, type DocumentFormValues } from "@/components/legal/DocumentFormModal";
import { DocumentPreviewModal } from "@/components/legal/DocumentPreviewModal";
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
  const [toast, setToast] = useState<string | null>(null);
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

  const [previewDoc, setPreviewDoc] = useState<LegalDocument | null>(null);
  const [signedDevisList, setSignedDevisList] = useState<LegalDocument[]>([]);
  const [selectedSignedDevisId, setSelectedSignedDevisId] = useState("");
  const [signedDevisPickerOpen, setSignedDevisPickerOpen] = useState(false);
  const [convertBusy, setConvertBusy] = useState(false);

  function openPreview(doc: LegalDocument) {
    setPreviewDoc(doc);
  }

  function reportActionError(message: string) {
    if (shouldSilenceApiError(message)) {
      logAccountingApiError(docTypeLabel, message);
    } else {
      setToast(message);
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    const [docsRes, clientsRes] = await Promise.all([
      fetchLegalDocuments({ type: docType }),
      fetchLegalClients(),
    ]);
    if (!docsRes.ok) {
      logAccountingApiError(
        docTypeLabel,
        apiErrorMessage(docsRes, "Impossible de charger les documents."),
      );
      setDocuments([]);
    } else {
      setDocuments(Array.isArray(docsRes.data) ? docsRes.data : []);
    }
    if (!clientsRes.ok) {
      logAccountingApiError(
        "Clients légaux",
        apiErrorMessage(clientsRes, "Impossible de charger les clients."),
      );
      setClients([]);
    } else {
      setClients(Array.isArray(clientsRes.data) ? clientsRes.data : []);
    }
    setLoading(false);
  }, [docType, docTypeLabel]);

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
    try {
      await fn();
      await load();
    } catch (err) {
      reportActionError(err instanceof Error ? err.message : "Action échouée.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleFromProject() {
    if (!selectedProjectId) return;
    setProjectBusy(true);
    const res = await createDocumentFromProject(selectedProjectId);
    setProjectBusy(false);
    if (!res.ok) {
      reportActionError(
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
    const res = await sendLegalDocument(sendDoc.id, { message: sendMessage });
    setSendBusy(false);
    if (!res.ok) {
      reportActionError(apiErrorMessage(res, "Envoi email impossible."));
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
      reportActionError(apiErrorMessage(res, "Changement de statut impossible."));
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
          className={GOLD_BTN}
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
            className={GLASS_BTN}
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
            className={GLASS_BTN}
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
        <button type="button" className={GLASS_BTN} onClick={() => void load()}>
          Actualiser
        </button>
      </div>

      {loading ? (
        <p className="animate-pulse text-sm text-white/50">Chargement…</p>
      ) : documents.length === 0 ? (
        <div className={`${GLASS_SECTION} flex flex-col items-center py-14 text-center`}>
          <FileText className="mb-3 h-10 w-10 text-white/20" aria-hidden />
          <p className="text-sm text-white/30">
            Aucun {docTypeLabel.toLowerCase()} pour le moment
          </p>
          {docType === "devis" ? (
            <button
              type="button"
              className={`${GOLD_BTN} mt-5`}
              onClick={() => {
                setEditDoc(null);
                setFormError(null);
                setFormOpen(true);
              }}
            >
              Créer un devis
            </button>
          ) : null}
        </div>
      ) : (
        <div className={`${GLASS_SECTION} overflow-x-auto p-0`}>
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase tracking-widest text-white/40">
                <th className="px-3 py-3 font-medium">Numéro</th>
                <th className="px-3 py-3 font-medium">Client</th>
                <th className="px-3 py-3 font-medium">Titre</th>
                <th className="px-3 py-3 text-right font-medium">TTC</th>
                <th className="px-3 py-3 font-medium">Statut</th>
                <th className="px-3 py-3 font-medium">Date</th>
                <th className="px-3 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="cursor-pointer border-b border-white/5 transition hover:bg-white/5"
                    onClick={() => openPreview(doc)}
                  >
                    <td className="px-3 py-3 font-mono text-xs text-[#d4a843]/90">
                      {doc.number}
                    </td>
                    <td className="px-3 py-3 text-white">
                      {clientName(clients, doc.client_id)}
                    </td>
                    <td className="max-w-[200px] truncate px-3 py-3 text-white/80" title={doc.title}>
                      {doc.title}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-white">
                      {formatEur(doc.total_ttc)}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-3 py-3 text-xs text-white/50">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex flex-wrap gap-1">
                        <ActionBtn
                          label="Aperçu"
                          title="Aperçu PDF"
                          onClick={() => openPreview(doc)}
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
                          label="Supprimer"
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
                ))}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0f0f0f]/95 p-6">
            <BackButton className="mb-3" onClick={() => setProjectPickerOpen(false)} />
            <h3 className="text-base font-semibold text-white">
              Devis depuis un projet
            </h3>
            <p className="mt-1 text-xs text-white/50">
              Pré-remplit titre, ligne et prix suggéré (P7).
            </p>
            <select
              className={`${SELECT} mt-4`}
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
                className={GLASS_BTN}
                onClick={() => setProjectPickerOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className={GOLD_BTN}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-[#0f0f0f]/95 p-6">
            <BackButton className="mb-3" onClick={() => setSendDoc(null)} />
            <h3 className="text-base font-semibold text-white">
              Envoyer {sendDoc.number}
            </h3>
            <p className="mt-1 text-xs text-white/50">
              Email vers {clientName(clients, sendDoc.client_id)}
            </p>
            <textarea
              className={`${INPUT} mt-3 min-h-[120px] resize-y`}
              value={sendMessage}
              onChange={(e) => setSendMessage(e.target.value)}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className={GLASS_BTN} onClick={() => setSendDoc(null)}>
                Annuler
              </button>
              <button
                type="button"
                className={GOLD_BTN}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0f0f0f]/95 p-6">
            <BackButton className="mb-3" onClick={() => setSignedDevisPickerOpen(false)} />
            <h3 className="text-base font-semibold text-white">
              Convertir en facture
            </h3>
            <p className="mt-1 text-xs text-white/50">
              Sélectionnez un devis au statut « signé ».
            </p>
            {signedDevisList.length === 0 ? (
              <p className="mt-4 text-sm text-white/30">
                Aucun devis signé disponible.
              </p>
            ) : (
              <select
                className={`${SELECT} mt-4`}
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
                className={GLASS_BTN}
                onClick={() => setSignedDevisPickerOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className={GOLD_BTN}
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
                    reportActionError(
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-white/10 bg-[#0f0f0f]/95 p-6">
            <BackButton className="mb-3" onClick={() => setStatusDoc(null)} />
            <h3 className="text-base font-semibold text-white">
              Statut — {statusDoc.number}
            </h3>
            <select
              className={`${SELECT} mt-3`}
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
              <button type="button" className={GLASS_BTN} onClick={() => setStatusDoc(null)}>
                Annuler
              </button>
              <button type="button" className={GOLD_BTN} onClick={() => void handleStatusSave()}>
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <DocumentPreviewModal
        doc={previewDoc}
        docTypeLabel={docTypeLabel}
        clients={clients}
        onClose={() => setPreviewDoc(null)}
        onDeleted={() => void load()}
        onUpdated={() => void load()}
      />

      <AccountingToast message={toast} onDismiss={() => setToast(null)} />
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
      className={`rounded-lg border border-white/15 bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-white/55 transition hover:border-[#d4a843]/40 hover:text-[#d4a843] disabled:opacity-40 ${className}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
