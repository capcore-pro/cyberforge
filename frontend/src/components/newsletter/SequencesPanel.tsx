import { useCallback, useEffect, useMemo, useState } from "react";
import type { ProjectRecord } from "@shared/types";
import { BackButton } from "@/components/BackButton";
import { EmailTimeline } from "@/components/newsletter/EmailTimeline";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchNewsletterContacts,
  fetchNewsletterSequences,
  fetchProjectsForNewsletter,
  fetchSequenceEmails,
  sendPendingNewsletterEmails,
  SEQUENCE_STATUS_LABELS,
  TRIGGER_LABELS,
  triggerWelcomeSequence,
  type NewsletterContact,
  type NewsletterEmail,
  type NewsletterSequence,
} from "@/lib/newsletter-api";

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function statusClass(status: string): string {
  if (status === "completed") return "bg-emerald-500/20 text-emerald-200 border-emerald-500/40";
  if (status === "in_progress") return "bg-blue-500/20 text-blue-200 border-blue-500/40";
  if (status === "cancelled") return "bg-red-500/20 text-red-200 border-red-500/40";
  return "bg-slate-500/20 text-slate-200 border-slate-500/40";
}

export function SequencesPanel() {
  const [sequences, setSequences] = useState<NewsletterSequence[]>([]);
  const [contacts, setContacts] = useState<NewsletterContact[]>([]);
  const [emailsBySeq, setEmailsBySeq] = useState<Record<string, NewsletterEmail[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");

  const contactMap = useMemo(
    () => new Map(contacts.map((c) => [c.id, c])),
    [contacts],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [seqRes, contactRes] = await Promise.all([
      fetchNewsletterSequences(),
      fetchNewsletterContacts(),
    ]);
    if (!seqRes.ok) {
      setError(apiErrorMessage(seqRes, "Impossible de charger les séquences."));
      setLoading(false);
      return;
    }
    if (!contactRes.ok) {
      setError(apiErrorMessage(contactRes, "Impossible de charger les contacts."));
      setLoading(false);
      return;
    }
    const seqs = Array.isArray(seqRes.data) ? seqRes.data : [];
    setSequences(seqs);
    setContacts(Array.isArray(contactRes.data) ? contactRes.data : []);

    const emailEntries = await Promise.all(
      seqs.map(async (s) => {
        const res = await fetchSequenceEmails(s.id);
        return [s.id, res.ok && Array.isArray(res.data) ? res.data : []] as const;
      }),
    );
    setEmailsBySeq(Object.fromEntries(emailEntries));
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openProjectPicker() {
    const res = await fetchProjectsForNewsletter();
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
      setSelectedProjectId(res.data[0]?.id ?? "");
    }
    setProjectPickerOpen(true);
  }

  async function handleTrigger() {
    if (!selectedProjectId) return;
    setBusy(true);
    setActionMsg(null);
    const res = await triggerWelcomeSequence(selectedProjectId);
    setBusy(false);
    setProjectPickerOpen(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Échec du déclenchement."));
      return;
    }
    setActionMsg(
      `Séquence créée — ${res.data?.emails_scheduled ?? 0} email(s), J0 envoyé : ${res.data?.j0_sent ? "oui" : "non"}.`,
    );
    await load();
  }

  async function handleSendPending() {
    setBusy(true);
    setActionMsg(null);
    const res = await sendPendingNewsletterEmails();
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Envoi en attente impossible."));
      return;
    }
    const d = res.data;
    setActionMsg(
      `Envoi terminé : ${d?.sent ?? 0} envoyé(s), ${d?.failed ?? 0} échec(s), ${d?.skipped ?? 0} ignoré(s).`,
    );
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary text-xs"
          disabled={busy}
          onClick={() => void openProjectPicker()}
        >
          Déclencher manuellement
        </button>
        <button
          type="button"
          className="cyber-action-btn text-xs"
          disabled={busy}
          onClick={() => void handleSendPending()}
        >
          Envoyer les emails en attente
        </button>
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
      {actionMsg ? (
        <p className="rounded border border-cyber-neon/30 bg-cyber-accent/10 px-3 py-2 text-sm text-cyber-neon">
          {actionMsg}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-cyber-muted animate-pulse">Chargement des séquences…</p>
      ) : (
        <div className="space-y-3">
          {sequences.length === 0 ? (
            <p className="text-sm text-cyber-muted">Aucune séquence pour le moment.</p>
          ) : (
            sequences.map((seq) => {
              const contact = contactMap.get(seq.contact_id);
              const emails = emailsBySeq[seq.id] ?? [];
              return (
                <div
                  key={seq.id}
                  className="cyber-panel border-cyber-border p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-cyber-text">
                        {contact?.name ?? "—"}
                        {contact?.company ? (
                          <span className="text-cyber-muted"> — {contact.company}</span>
                        ) : null}
                      </p>
                      <p className="text-xs text-cyber-muted">
                        {TRIGGER_LABELS[seq.trigger] ?? seq.trigger} ·{" "}
                        {formatDate(seq.created_at)}
                      </p>
                    </div>
                    <span
                      className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${statusClass(seq.status)}`}
                    >
                      {SEQUENCE_STATUS_LABELS[seq.status] ?? seq.status}
                    </span>
                  </div>
                  <EmailTimeline emails={emails} />
                </div>
              );
            })
          )}
        </div>
      )}

      {projectPickerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="cyber-panel w-full max-w-md border-cyber-violet/40">
            <BackButton
              className="mb-3"
              onClick={() => setProjectPickerOpen(false)}
            />
            <h3 className="text-base font-semibold text-cyber-text">
              Déclencher une séquence bienvenue
            </h3>
            <select
              className="cyber-input mt-4 w-full"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">— Projet —</option>
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
                disabled={!selectedProjectId || busy}
                onClick={() => void handleTrigger()}
              >
                {busy ? "…" : "Déclencher"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
