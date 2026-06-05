import { useCallback, useEffect, useState } from "react";
import { Eye } from "lucide-react";
import { BackButton } from "@/components/BackButton";
import {
  BADGE_GLASS,
  FIELD_LABEL,
  GLASS_PILL_BTN,
  GLASS_SECTION,
  GOLD_BTN,
  INPUT,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchNewsletterContacts,
  generateNewsletterEmail,
  previewNewsletterEmail,
  sendNewsletterToAll,
  type NewsletterEmail,
} from "@/lib/newsletter-api";

function reportError(context: string, res: { ok: boolean; status?: number }) {
  const msg = apiErrorMessage(res, `${context} impossible.`);
  logAccountingApiError(`Newsletter / ${context}`, msg);
  return shouldSilenceApiError(msg) ? null : msg;
}

export function NewsletterBroadcastPanel() {
  const [theme, setTheme] = useState("");
  const [context, setContext] = useState("");
  const [draft, setDraft] = useState<NewsletterEmail | null>(null);
  const [subscriberCount, setSubscriberCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadSubscribers = useCallback(async () => {
    const res = await fetchNewsletterContacts();
    if (res.ok && Array.isArray(res.data)) {
      setSubscriberCount(res.data.filter((c) => c.subscribed).length);
    } else if (!res.ok) {
      reportError("abonnés", res);
    }
  }, []);

  useEffect(() => {
    void loadSubscribers();
  }, [loadSubscribers]);

  async function handleGenerate() {
    if (!theme.trim()) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    const res = await generateNewsletterEmail({
      theme: theme.trim(),
      context: context.trim(),
    });
    setLoading(false);
    if (!res.ok) {
      setError(reportError("génération", res));
      return;
    }
    setDraft(res.data ?? null);
    setMessage("Newsletter générée (brouillon).");
  }

  async function handlePreview() {
    if (!draft) return;
    setLoading(true);
    setError(null);
    const res = await previewNewsletterEmail(draft.id);
    setLoading(false);
    if (!res.ok) {
      setError(reportError("preview", res));
      return;
    }
    setMessage(`Preview envoyée à ${res.data?.to ?? "Mat"}.`);
  }

  async function handleSendAll() {
    if (!draft) return;
    if (
      !window.confirm(
        `Envoyer cette newsletter à ${subscriberCount} abonné(s) actif(s) ?`,
      )
    ) {
      return;
    }
    setLoading(true);
    setError(null);
    const res = await sendNewsletterToAll(draft.id);
    setLoading(false);
    if (!res.ok) {
      setError(reportError("envoi global", res));
      return;
    }
    setMessage(
      `Envoi : ${res.data?.sent ?? 0} / ${res.data?.recipients ?? 0} (${res.data?.failed ?? 0} échec(s)).`,
    );
    void loadSubscribers();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_1fr]">
      <div className={`${GLASS_SECTION} space-y-4 p-6`}>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
          Nouvelle newsletter
        </h3>
        <span className={BADGE_GLASS}>
          Abonnés actifs : {subscriberCount}
        </span>
        <div>
          <label className={FIELD_LABEL}>Thème</label>
          <input
            className={INPUT}
            placeholder="Ex. nouvelle fonctionnalité clone de site"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
          />
        </div>
        <div>
          <label className={FIELD_LABEL}>Contexte (optionnel)</label>
          <textarea
            className={`${INPUT} min-h-[120px] resize-none`}
            placeholder="Détails pour l'agent…"
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
        </div>
        <button
          type="button"
          className={`${GOLD_BTN} mt-2 w-full py-2.5 font-medium`}
          disabled={loading || !theme.trim()}
          onClick={() => void handleGenerate()}
        >
          {loading ? "Génération…" : "Générer"}
        </button>
        {draft ? (
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              className={GLASS_PILL_BTN}
              disabled={loading}
              onClick={() => void handlePreview()}
            >
              Envoyer preview à Mat
            </button>
            <button
              type="button"
              className={GLASS_PILL_BTN}
              disabled={loading || subscriberCount === 0}
              onClick={() => void handleSendAll()}
            >
              Envoyer à tous les abonnés
            </button>
          </div>
        ) : null}
        {error ? (
          <p className="text-sm text-red-300">{error}</p>
        ) : null}
        {message ? (
          <p className="rounded-lg border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-[#d4a843]">
            {message}
          </p>
        ) : null}
      </div>

      <div className={`${GLASS_SECTION} flex min-h-[320px] flex-col p-6`}>
        {draft ? (
          <BackButton
            className="mb-3 self-start"
            onClick={() => {
              setDraft(null);
              setMessage(null);
              setError(null);
            }}
          />
        ) : null}
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
          Aperçu HTML
        </h3>
        {draft ? (
          <>
            <p className="mb-3 text-sm font-medium text-white">{draft.subject}</p>
            <div className="flex-1 overflow-hidden rounded-lg border border-white/10 bg-white">
              <iframe
                title="Aperçu newsletter"
                className="h-[min(520px,60vh)] w-full bg-white"
                sandbox=""
                srcDoc={draft.html_content}
              />
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
            <Eye className="mb-3 h-10 w-10 text-white/20" aria-hidden />
            <p className="text-sm text-white/30">
              Générez une newsletter pour voir l&apos;aperçu ici
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
