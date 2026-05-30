import { useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  deleteLegalDocument,
  generateDocumentPdf,
  getDocumentPdfUrl,
  sendLegalDocument,
  type LegalClient,
  type LegalDocument,
} from "@/lib/legal-api";

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

export interface DocumentPreviewModalProps {
  doc: LegalDocument | null;
  docTypeLabel: string;
  clients: LegalClient[];
  onClose: () => void;
  onDeleted: () => void;
  onUpdated: () => void;
}

export function DocumentPreviewModal({
  doc,
  docTypeLabel,
  clients,
  onClose,
  onDeleted,
  onUpdated,
}: DocumentPreviewModalProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const [sendMessage, setSendMessage] = useState("");

  const clientLabel =
    doc?.client_id != null
      ? clients.find((c) => c.id === doc.client_id)?.name ?? "—"
      : "—";

  useEffect(() => {
    if (!doc) {
      setPdfUrl(null);
      setError(null);
      setConfirmDelete(false);
      setSendOpen(false);
      return;
    }

    let cancelled = false;

    async function ensurePdf() {
      setLoading(true);
      setError(null);
      setPdfUrl(null);

      if (!doc!.pdf_path && !doc!.pdf_url) {
        const gen = await generateDocumentPdf(doc!.id);
        if (cancelled) return;
        if (!gen.ok) {
          setError(apiErrorMessage(gen, "Génération PDF impossible."));
          setLoading(false);
          return;
        }
        onUpdated();
        const generatedUrl = gen.data?.pdf_url
          ? getDocumentPdfUrl({ ...doc!, pdf_url: gen.data.pdf_url })
          : getDocumentPdfUrl(doc!);
        setPdfUrl(`${generatedUrl}${generatedUrl.includes("?") ? "&" : "?"}t=${Date.now()}`);
        setLoading(false);
        return;
      }

      const url = getDocumentPdfUrl(doc!);
      setPdfUrl(`${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`);
      setLoading(false);
    }

    void ensurePdf();
    return () => {
      cancelled = true;
    };
  }, [doc?.id]);

  useEffect(() => {
    if (!doc) return;
    setSendMessage(
      doc.type === "devis"
        ? "Veuillez trouver ci-joint notre devis. Nous restons à votre disposition."
        : "Veuillez trouver ci-joint votre facture. Merci pour votre confiance.",
    );
  }, [doc?.id, doc?.type]);

  if (!doc) return null;

  async function handleSend() {
    setBusy(true);
    setError(null);
    const res = await sendLegalDocument(doc!.id, { message: sendMessage });
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Envoi email impossible."));
      return;
    }
    setSendOpen(false);
    onUpdated();
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setBusy(true);
    setError(null);
    const res = await deleteLegalDocument(doc!.id);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Suppression impossible."));
      setConfirmDelete(false);
      return;
    }
    onDeleted();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal
      aria-labelledby="doc-preview-title"
      onClick={onClose}
    >
      <div
        className="cyber-panel flex max-h-[95vh] w-full max-w-5xl flex-col overflow-hidden border-cyber-neon/30"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-cyber-border px-4 py-3">
          <BackButton label="Fermer" onClick={onClose} />
          <div className="min-w-0 flex-1 px-4 text-center">
            <h2 id="doc-preview-title" className="truncate text-sm font-medium text-cyber-text">
              {doc.number} — {doc.title}
            </h2>
            <p className="text-[10px] text-cyber-muted">
              {clientLabel} · {formatEur(doc.total_ttc)}
            </p>
          </div>
          <span className="w-16" aria-hidden />
        </div>

        <div className="min-h-[320px] flex-1 bg-cyber-bg/80">
          {loading ? (
            <p className="flex h-full items-center justify-center text-sm text-cyber-muted animate-pulse">
              Génération de l&apos;aperçu PDF…
            </p>
          ) : error && !pdfUrl ? (
            <p className="flex h-full items-center justify-center px-4 text-sm text-red-200">
              {error}
            </p>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              title={`Aperçu ${docTypeLabel} ${doc.number}`}
              className="h-full min-h-[50vh] w-full border-0"
            />
          ) : null}
        </div>

        {error && pdfUrl ? (
          <p className="border-t border-red-500/30 bg-red-950/20 px-4 py-2 text-xs text-red-200">
            {error}
          </p>
        ) : null}

        {sendOpen ? (
          <div className="border-t border-cyber-border bg-cyber-surface/90 p-4">
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-cyber-muted">
              Message email (Brevo)
            </p>
            <textarea
              className="cyber-input min-h-[80px] w-full resize-y text-sm"
              value={sendMessage}
              onChange={(e) => setSendMessage(e.target.value)}
            />
            <div className="mt-2 flex justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn text-xs"
                onClick={() => setSendOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary text-xs"
                disabled={busy || !sendMessage.trim() || !doc.client_id}
                onClick={() => void handleSend()}
              >
                {busy ? "Envoi…" : "Envoyer"}
              </button>
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2 border-t border-cyber-border p-4">
          {pdfUrl ? (
            <a
              href={pdfUrl}
              download={`${doc.number}.pdf`}
              className="cyber-action-btn text-xs"
            >
              Télécharger le PDF
            </a>
          ) : null}
          <button
            type="button"
            className="cyber-action-btn text-xs"
            disabled={busy || !doc.client_id}
            title={!doc.client_id ? "Associez un client pour envoyer" : undefined}
            onClick={() => setSendOpen((v) => !v)}
          >
            Envoyer par email
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleDelete()}
            className={`cyber-action-btn text-xs ${
              confirmDelete
                ? "border-red-500 bg-red-950/50 text-red-200"
                : "border-red-500/40 text-red-300"
            }`}
          >
            {confirmDelete ? "Confirmer la suppression" : "Supprimer"}
          </button>
          {confirmDelete ? (
            <button
              type="button"
              className="cyber-action-btn text-xs"
              onClick={() => setConfirmDelete(false)}
            >
              Annuler
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
