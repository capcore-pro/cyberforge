import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchNewsletterContacts,
  generateNewsletterEmail,
  previewNewsletterEmail,
  sendNewsletterToAll,
  type NewsletterEmail,
} from "@/lib/newsletter-api";

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
      setError(apiErrorMessage(res, "Génération impossible."));
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
      setError(apiErrorMessage(res, "Preview impossible."));
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
      setError(apiErrorMessage(res, "Envoi global impossible."));
      return;
    }
    setMessage(
      `Envoi : ${res.data?.sent ?? 0} / ${res.data?.recipients ?? 0} (${res.data?.failed ?? 0} échec(s)).`,
    );
    void loadSubscribers();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_1fr]">
      <div className="cyber-panel space-y-4 border-cyber-border p-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-neon">
          Nouvelle newsletter
        </h3>
        <p className="text-xs text-cyber-muted">
          Abonnés actifs :{" "}
          <span className="font-mono text-cyber-text">{subscriberCount}</span>
        </p>
        <div>
          <label className="mb-1 block text-xs font-bold uppercase text-cyber-muted">
            Thème
          </label>
          <input
            className="cyber-input w-full"
            placeholder="Ex. nouvelle fonctionnalité clone de site"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-bold uppercase text-cyber-muted">
            Contexte (optionnel)
          </label>
          <textarea
            className="cyber-input min-h-[100px] w-full resize-y"
            placeholder="Détails pour l'agent…"
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary w-full text-xs"
          disabled={loading || !theme.trim()}
          onClick={() => void handleGenerate()}
        >
          {loading ? "Génération…" : "Générer"}
        </button>
        {draft ? (
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              className="cyber-action-btn text-xs"
              disabled={loading}
              onClick={() => void handlePreview()}
            >
              Envoyer preview à Mat
            </button>
            <button
              type="button"
              className="cyber-action-btn text-xs"
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
          <p className="text-sm text-cyber-neon">{message}</p>
        ) : null}
      </div>

      <div className="cyber-panel flex min-h-[320px] flex-col border-cyber-border p-4">
        <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-cyber-muted">
          Aperçu HTML
        </h3>
        {draft ? (
          <>
            <p className="mb-3 text-sm font-medium text-cyber-text">{draft.subject}</p>
            <div className="flex-1 overflow-hidden rounded-lg border border-cyber-border bg-white">
              <iframe
                title="Aperçu newsletter"
                className="h-[min(520px,60vh)] w-full bg-white"
                sandbox=""
                srcDoc={draft.html_content}
              />
            </div>
          </>
        ) : (
          <p className="text-sm text-cyber-muted">
            Générez une newsletter pour voir l&apos;aperçu ici.
          </p>
        )}
      </div>
    </div>
  );
}
