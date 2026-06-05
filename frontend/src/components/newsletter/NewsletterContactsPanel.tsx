import { useCallback, useEffect, useState } from "react";
import { Users } from "lucide-react";
import { BackButton } from "@/components/BackButton";
import {
  FORM_CONTAINER,
  GLASS_PILL_BTN,
  GLASS_SECTION,
  GOLD_BTN,
  INPUT,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createNewsletterContact,
  deleteNewsletterContact,
  fetchNewsletterContacts,
  updateNewsletterContact,
  type NewsletterContact,
} from "@/lib/newsletter-api";

const emptyForm = { name: "", email: "", company: "", sector: "" };

function reportError(context: string, res: { ok: boolean; status?: number }) {
  const msg = apiErrorMessage(res, `${context} impossible.`);
  logAccountingApiError(`Newsletter / ${context}`, msg);
  return shouldSilenceApiError(msg) ? null : msg;
}

export function NewsletterContactsPanel() {
  const [contacts, setContacts] = useState<NewsletterContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchNewsletterContacts();
    if (!res.ok) {
      setError(reportError("contacts", res));
      setContacts([]);
      setLoading(false);
      return;
    }
    setContacts(Array.isArray(res.data) ? res.data : []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) return;
    setBusy(true);
    const res = await createNewsletterContact({
      name: form.name.trim(),
      email: form.email.trim(),
      company: form.company.trim() || null,
      sector: form.sector.trim() || null,
      subscribed: true,
    });
    setBusy(false);
    if (!res.ok) {
      setError(reportError("création", res));
      return;
    }
    setForm(emptyForm);
    setShowForm(false);
    await load();
  }

  async function toggleSubscribed(contact: NewsletterContact) {
    const res = await updateNewsletterContact(contact.id, {
      subscribed: !contact.subscribed,
    });
    if (!res.ok) {
      setError(reportError("mise à jour", res));
      return;
    }
    await load();
  }

  async function handleDelete(contact: NewsletterContact) {
    if (
      !window.confirm(`Supprimer ${contact.name} (${contact.email}) ?`)
    ) {
      return;
    }
    const res = await deleteNewsletterContact(contact.id);
    if (!res.ok) {
      setError(reportError("suppression", res));
      return;
    }
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={GOLD_BTN}
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Fermer le formulaire" : "Ajouter contact"}
        </button>
        <button
          type="button"
          className={GLASS_PILL_BTN}
          onClick={() => void load()}
        >
          Actualiser
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={handleAdd}
          className={`${FORM_CONTAINER} grid gap-3 sm:grid-cols-2`}
        >
          <div className="sm:col-span-2">
            <BackButton
              className="mb-1"
              onClick={() => {
                setShowForm(false);
                setForm(emptyForm);
              }}
            />
          </div>
          <input
            className={INPUT}
            placeholder="Nom *"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />
          <input
            className={INPUT}
            type="email"
            placeholder="Email *"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
          />
          <input
            className={INPUT}
            placeholder="Entreprise"
            value={form.company}
            onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
          />
          <input
            className={INPUT}
            placeholder="Secteur"
            value={form.sector}
            onChange={(e) => setForm((f) => ({ ...f, sector: e.target.value }))}
          />
          <div className="sm:col-span-2">
            <button
              type="submit"
              className={GOLD_BTN}
              disabled={busy}
            >
              {busy ? "…" : "Enregistrer"}
            </button>
          </div>
        </form>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="animate-pulse text-sm text-white/50">Chargement…</p>
      ) : (
        <div className={`${GLASS_SECTION} overflow-x-auto p-0`}>
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs font-semibold uppercase tracking-widest text-white/40">
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">Entreprise</th>
                <th className="px-4 py-3">Secteur</th>
                <th className="px-4 py-3">Abonné</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {contacts.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="flex flex-col items-center py-12 text-center">
                      <Users className="mb-3 h-10 w-10 text-white/20" aria-hidden />
                      <p className="text-sm text-white/30">Aucun contact.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                contacts.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-white/5 transition-colors hover:bg-white/5"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{c.name}</div>
                      <div className="text-xs text-white/45">{c.email}</div>
                    </td>
                    <td className="px-4 py-3 text-white/70">{c.company || "—"}</td>
                    <td className="px-4 py-3 text-white/70">{c.sector || "—"}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={c.subscribed}
                        className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase ${
                          c.subscribed
                            ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
                            : "border-white/20 bg-white/10 text-white/55"
                        }`}
                        onClick={() => void toggleSubscribed(c)}
                      >
                        {c.subscribed ? "Oui" : "Non"}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="text-xs text-red-300/80 transition hover:text-red-300"
                        onClick={() => void handleDelete(c)}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
