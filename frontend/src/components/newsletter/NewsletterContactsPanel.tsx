import { useCallback, useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createNewsletterContact,
  deleteNewsletterContact,
  fetchNewsletterContacts,
  updateNewsletterContact,
  type NewsletterContact,
} from "@/lib/newsletter-api";

const emptyForm = { name: "", email: "", company: "", sector: "" };

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
      setError(apiErrorMessage(res, "Impossible de charger les contacts."));
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
      setError(apiErrorMessage(res, "Création impossible."));
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
      setError(apiErrorMessage(res, "Mise à jour impossible."));
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
      setError(apiErrorMessage(res, "Suppression impossible."));
      return;
    }
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary text-xs"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Fermer le formulaire" : "Ajouter contact"}
        </button>
        <button
          type="button"
          className="cyber-action-btn text-xs"
          onClick={() => void load()}
        >
          Actualiser
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={handleAdd}
          className="cyber-panel grid gap-3 border-cyber-neon/20 p-4 sm:grid-cols-2"
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
            className="cyber-input"
            placeholder="Nom *"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />
          <input
            className="cyber-input"
            type="email"
            placeholder="Email *"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
          />
          <input
            className="cyber-input"
            placeholder="Entreprise"
            value={form.company}
            onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
          />
          <input
            className="cyber-input"
            placeholder="Secteur"
            value={form.sector}
            onChange={(e) => setForm((f) => ({ ...f, sector: e.target.value }))}
          />
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="cyber-action-btn cyber-action-btn-primary text-xs"
              disabled={busy}
            >
              {busy ? "…" : "Enregistrer"}
            </button>
          </div>
        </form>
      ) : null}

      {error ? (
        <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-cyber-muted animate-pulse">Chargement…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-cyber-border">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-cyber-border bg-cyber-surface/80 text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
                <th className="px-3 py-2">Nom</th>
                <th className="px-3 py-2">Entreprise</th>
                <th className="px-3 py-2">Secteur</th>
                <th className="px-3 py-2">Abonné</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {contacts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-cyber-muted">
                    Aucun contact.
                  </td>
                </tr>
              ) : (
                contacts.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                  >
                    <td className="px-3 py-2">
                      <div className="font-medium text-cyber-text">{c.name}</div>
                      <div className="text-xs text-cyber-muted">{c.email}</div>
                    </td>
                    <td className="px-3 py-2">{c.company || "—"}</td>
                    <td className="px-3 py-2">{c.sector || "—"}</td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={c.subscribed}
                        className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase ${
                          c.subscribed
                            ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-200"
                            : "border-slate-500/50 bg-slate-500/20 text-slate-300"
                        }`}
                        onClick={() => void toggleSubscribed(c)}
                      >
                        {c.subscribed ? "Oui" : "Non"}
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        className="cyber-action-btn text-[10px] text-red-300"
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
