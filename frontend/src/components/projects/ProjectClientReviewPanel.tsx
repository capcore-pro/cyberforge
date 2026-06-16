import { useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Button } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { apiErrorMessage } from "@/lib/api-errors";
import { copyTextToClipboard } from "@/lib/generation-export";
import {
  createReview,
  getProjectReviews,
  type ClientReviewCreateResult,
  type ClientReviewRecord,
} from "@/lib/client-review-api";

interface ProjectClientReviewPanelProps {
  projectId: string;
  projectName: string;
  demoUrl: string | null;
}

function formatReviewDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function reviewStatusBadge(status: string) {
  if (status === "approved") {
    return (
      <span className="rounded-full border border-emerald-500/40 bg-emerald-950/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
        Approuvé ✓
      </span>
    );
  }
  if (status === "revision_requested") {
    return (
      <span className="rounded-full border border-amber-500/40 bg-amber-950/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
        Révisions ↩
      </span>
    );
  }
  return (
    <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-cf-muted">
      En attente
    </span>
  );
}

function ReviewRow({ review }: { review: ClientReviewRecord }) {
  return (
    <div className="rounded-control border border-cf-border-input bg-cf-secondary/40 p-3 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {reviewStatusBadge(review.status)}
        <span className="text-[11px] text-cf-muted">
          Créé {formatReviewDate(review.created_at)}
        </span>
      </div>
      <p className="text-xs text-cf-muted">
        Consulté : {formatReviewDate(review.viewed_at)}
      </p>
      {review.rating ? (
        <p className="text-sm text-cf-gold">{"★".repeat(review.rating)}</p>
      ) : null}
      {review.feedback ? (
        <p className="text-sm text-cf-text whitespace-pre-wrap">{review.feedback}</p>
      ) : null}
      {review.client_name ? (
        <p className="text-[11px] text-cf-muted">Client : {review.client_name}</p>
      ) : null}
    </div>
  );
}

export function ProjectClientReviewPanel({
  projectId,
  projectName,
  demoUrl,
}: ProjectClientReviewPanelProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<ClientReviewCreateResult | null>(null);
  const [copyOk, setCopyOk] = useState(false);
  const [reviews, setReviews] = useState<ClientReviewRecord[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  const loadReviews = useCallback(async () => {
    setReviewsLoading(true);
    const res = await getProjectReviews(projectId);
    setReviewsLoading(false);
    if (res.ok && res.data) {
      setReviews(res.data.items);
    }
  }, [projectId]);

  useEffect(() => {
    void loadReviews();
  }, [loadReviews]);

  async function handleGenerateLink() {
    setBusy(true);
    setError(null);
    const res = await createReview(
      projectId,
      clientName || projectName,
      clientEmail || undefined,
    );
    setBusy(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Impossible de générer le lien."));
      return;
    }
    setCreated(res.data);
    void loadReviews();
  }

  async function handleCopyLink() {
    if (!created?.review_url) return;
    try {
      await copyTextToClipboard(created.review_url);
      setCopyOk(true);
      window.setTimeout(() => setCopyOk(false), 2000);
    } catch {
      setError("Copie impossible.");
    }
  }

  function handleWhatsAppShare() {
    if (!created?.review_url) return;
    const text = encodeURIComponent(
      `Votre site est prêt ! Validez-le ici : ${created.review_url}`,
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  }

  if (!demoUrl) {
    return null;
  }

  return (
    <>
      <div className="mt-3">
        <Button
          variant="ghost"
          size="sm"
          icon="ti ti-send"
          onClick={() => {
            setModalOpen(true);
            setCreated(null);
            setError(null);
            setClientName("");
            setClientEmail("");
          }}
        >
          Envoyer au client
        </Button>
      </div>

      <div className="mt-6 space-y-3">
        <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
          Reviews clients
        </p>
        {reviewsLoading ? (
          <p className="text-xs text-cf-muted animate-pulse">Chargement…</p>
        ) : reviews.length === 0 ? (
          <p className="text-sm text-cf-muted">Aucune review envoyée pour ce projet.</p>
        ) : (
          <div className="space-y-2">
            {reviews.map((review) => (
              <ReviewRow key={review.id} review={review} />
            ))}
          </div>
        )}
      </div>

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Envoyer au client"
        subtitle="Lien de validation mobile — valable 30 jours"
        icon="ti ti-link"
        size="md"
      >
        {!created ? (
          <div className="space-y-4">
            <label className="block space-y-1.5">
              <span className="text-xs text-cf-muted">Nom client (optionnel)</span>
              <input
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder={projectName}
                className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-xs text-cf-muted">Email client (optionnel)</span>
              <input
                type="email"
                value={clientEmail}
                onChange={(e) => setClientEmail(e.target.value)}
                className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
              />
            </label>
            {error ? <p className="text-xs text-red-300">{error}</p> : null}
            <Button
              variant="primary"
              className="w-full"
              loading={busy}
              onClick={() => void handleGenerateLink()}
            >
              Générer le lien
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="break-all rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-[#d4a843]">
              {created.review_url}
            </p>
            <p className="text-xs text-cf-muted">
              Expire le {formatReviewDate(created.expires_at)}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button variant="ghost" size="sm" onClick={() => void handleCopyLink()}>
                {copyOk ? "Copié ✓" : "Copier le lien"}
              </Button>
              <Button variant="ghost" size="sm" onClick={handleWhatsAppShare}>
                Partager via WhatsApp
              </Button>
            </div>
            <div className="flex justify-center rounded-card border border-white/10 bg-white p-4">
              <QRCodeSVG value={created.review_url} size={180} />
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
