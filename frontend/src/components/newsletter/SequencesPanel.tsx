import { useCallback, useEffect, useMemo, useState } from "react";
import { Mail } from "lucide-react";
import type { ProjectRecord } from "@shared/types";
import { BackButton } from "@/components/BackButton";
import { EmailTimeline } from "@/components/newsletter/EmailTimeline";
import {
  GLASS_PILL_BTN,
  GLASS_SECTION,
  GOLD_BTN,
  SELECT,
  logAccountingApiError,
} from "@/components/accounting/accounting-theme";
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
  if (status === "completed")
    return "border-emerald-400/35 bg-emerald-500/15 text-emerald-300";
  if (status === "in_progress")
    return "border-blue-400/35 bg-blue-500/15 text-blue-300";
  if (status === "cancelled")
    return "border-red-400/35 bg-red-500/15 text-red-300";
  return "border-white/20 bg-white/10 text-white/55";
}

export function SequencesPanel() {
  const [sequences, setSequences] = useState<NewsletterSequence[]>([]);
  const [contacts, setContacts] = useState<NewsletterContact[]>([]);
  const [emailsBySeq, setEmailsBySeq] = useState<Record<string, NewsletterEmail[]>>({});
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");

  const contactMap = useMemo(
    () => new Map(contacts.map((c) => [c.id, c])),
    [contacts],
  );

  function reportError(context: string, res: { ok: boolean; status?: number }) {
    const msg = apiErrorMessage(res, `${context} impossible.`);
    logAccountingApiError(`Newsletter / ${context}`, msg);
  }

  const load = useCallback(async () => {
    setLoading(true);
    const [seqRes, contactRes] = await Promise.all([
      fetchNewsletterSequences(),
      fetchNewsletterContacts(),
    ]);
    if (!seqRes.ok) {
      reportError("séquences", seqRes);
      setSequences([]);
    } else {
      const seqs = Array.isArray(seqRes.data) ? seqRes.data : [];
      setSequences(seqs);
      const emailEntries = await Promise.all(
        seqs.map(async (s) => {
          const res = await fetchSequenceEmails(s.id);
          return [s.id, res.ok && Array.isArray(res.data) ? res.data : []] as const;
        }),
      );
      setEmailsBySeq(Object.fromEntries(emailEntries));
    }
    if (!contactRes.ok) {
      reportError("contacts", contactRes);
      setContacts([]);
    } else {
      setContacts(Array.isArray(contactRes.data) ? contactRes.data : []);
    }
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
      reportError("déclenchement", res);
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
      reportError("envoi en attente", res);
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
          className={GOLD_BTN}
          disabled={busy}
          onClick={() => void openProjectPicker()}
        >
          Déclencher manuellement
        </button>
        <button
          type="button"
          className={GLASS_PILL_BTN}
          disabled={busy}
          onClick={() => void handleSendPending()}
        >
          Envoyer les emails en attente
        </button>
        <button
          type="button"
          className={GLASS_PILL_BTN}
          onClick={() => void load()}
        >
          Actualiser
        </button>
      </div>

      {actionMsg ? (
        <p className="rounded-lg border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-[#d4a843]">
          {actionMsg}
        </p>
      ) : null}

      {loading ? (
        <p className="animate-pulse text-sm text-white/50">
          Chargement des séquences…
        </p>
      ) : sequences.length === 0 ? (
        <div
          className={`${GLASS_SECTION} flex flex-col items-center py-14 text-center`}
        >
          <Mail className="mb-3 h-10 w-10 text-white/20" aria-hidden />
          <p className="text-sm text-white/30">Aucune séquence pour le moment</p>
          <button
            type="button"
            className={`${GOLD_BTN} mt-5`}
            onClick={() => void openProjectPicker()}
          >
            Créer une séquence
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {sequences.map((seq) => {
            const contact = contactMap.get(seq.contact_id);
            const emails = emailsBySeq[seq.id] ?? [];
            return (
              <div key={seq.id} className={`${GLASS_SECTION} space-y-2`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-white">
                      {contact?.name ?? "—"}
                      {contact?.company ? (
                        <span className="text-white/50">
                          {" "}
                          — {contact.company}
                        </span>
                      ) : null}
                    </p>
                    <p className="text-xs text-white/45">
                      {TRIGGER_LABELS[seq.trigger] ?? seq.trigger} ·{" "}
                      {formatDate(seq.created_at)}
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${statusClass(seq.status)}`}
                  >
                    {SEQUENCE_STATUS_LABELS[seq.status] ?? seq.status}
                  </span>
                </div>
                <EmailTimeline emails={emails} />
              </div>
            );
          })}
        </div>
      )}

      {projectPickerOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0f0f0f]/95 p-6">
            <BackButton
              className="mb-3"
              onClick={() => setProjectPickerOpen(false)}
            />
            <h3 className="text-base font-semibold text-white">
              Déclencher une séquence bienvenue
            </h3>
            <select
              className={`${SELECT} mt-4`}
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
                className={GLASS_PILL_BTN}
                onClick={() => setProjectPickerOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className={GOLD_BTN}
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
