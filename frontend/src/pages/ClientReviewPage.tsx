import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  getReview,
  respondToReview,
  type ClientReviewPublic,
} from "@/lib/client-review-api";

interface ClientReviewPageProps {
  token: string;
}

function StarRating({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-center gap-2" role="group" aria-label="Note">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          className={`text-3xl transition ${
            star <= value ? "text-cf-gold" : "text-white/20"
          } disabled:cursor-not-allowed`}
          aria-label={`${star} étoile${star > 1 ? "s" : ""}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

/**
 * Page publique client — /review/{token}, validation mobile-first.
 */
export function ClientReviewPage({ token }: ClientReviewPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<ClientReviewPublic | null>(null);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const loadReview = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await getReview(token);
    setLoading(false);
    if (!response.ok || !response.data) {
      const status = response.status;
      if (status === 410) {
        setError("Ce lien a expiré — contactez CapCore");
        return;
      }
      setError(
        apiErrorMessage(response, "Lien invalide ou expiré — contactez CapCore"),
      );
      return;
    }
    setReview(response.data);
    if (response.data.rating) {
      setRating(response.data.rating);
    }
  }, [token]);

  useEffect(() => {
    void loadReview();
  }, [loadReview]);

  async function handleRespond(status: "approved" | "revision_requested") {
    setSubmitting(true);
    setError(null);
    const response = await respondToReview(
      token,
      status,
      feedback,
      rating > 0 ? rating : undefined,
    );
    setSubmitting(false);
    if (!response.ok || !response.data) {
      setError(apiErrorMessage(response, "Envoi impossible. Réessayez."));
      return;
    }
    setConfirmation(response.data.message);
    setReview((prev) =>
      prev
        ? {
            ...prev,
            status,
            responded: true,
            rating: rating > 0 ? rating : prev.rating,
            feedback: feedback.trim() || prev.feedback,
          }
        : prev,
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0f1117] px-4">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-cf-gold border-t-transparent" />
      </div>
    );
  }

  if (error && !review) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0f1117] px-6 text-center">
        <div className="max-w-md space-y-3">
          <p className="text-lg font-semibold text-white">CapCore</p>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      </div>
    );
  }

  if (!review) {
    return null;
  }

  const alreadyResponded = review.responded || review.status !== "pending";
  const demoUrl = review.demo_url?.trim() || "";

  return (
    <div className="min-h-screen bg-[#0f1117] text-white">
      <header className="border-b border-white/10 px-4 py-5 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cf-gold">
          CapCore
        </p>
        <h1 className="mt-2 text-2xl font-semibold">Votre projet est prêt !</h1>
        <p className="mt-1 text-sm text-white/60">{review.project_title}</p>
      </header>

      {demoUrl ? (
        <section className="border-b border-white/10">
          <iframe
            title={review.project_title}
            src={demoUrl}
            className="h-[60vh] w-full border-0 bg-white"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
          <div className="px-4 py-3">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => window.open(demoUrl, "_blank")}
            >
              Ouvrir en grand ↗
            </Button>
          </div>
        </section>
      ) : null}

      <section className="mx-auto max-w-lg px-4 py-6">
        {confirmation ? (
          <div className="rounded-card border border-emerald-500/30 bg-emerald-950/30 p-5 text-center">
            <p className="text-base text-emerald-200">{confirmation}</p>
          </div>
        ) : alreadyResponded ? (
          <div className="rounded-card border border-white/10 bg-white/5 p-5 text-center">
            <p className="text-base text-white/80">
              Merci pour votre réponse ! Nous avons bien reçu votre avis.
            </p>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="text-center">
              <p className="text-lg font-medium">Que pensez-vous du site ?</p>
              <div className="mt-4">
                <StarRating value={rating} onChange={setRating} disabled={submitting} />
              </div>
            </div>

            <label className="block space-y-2">
              <span className="text-sm text-white/60">Vos commentaires (optionnel)</span>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={4}
                disabled={submitting}
                className="w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cf-gold/50 focus:outline-none"
                placeholder="Dites-nous ce que vous en pensez…"
              />
            </label>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}

            <Button
              variant="success"
              size="lg"
              className="w-full"
              loading={submitting}
              onClick={() => void handleRespond("approved")}
            >
              ✓ J&apos;approuve ce site
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              loading={submitting}
              onClick={() => void handleRespond("revision_requested")}
            >
              ↩ Demander des révisions
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
