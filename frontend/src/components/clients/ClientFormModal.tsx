import { useEffect, useState } from "react";

export interface ClientFormValues {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  company: string;
  website: string;
  address: string;
  notes: string;
  active: boolean;
}

interface ClientFormModalProps {
  open: boolean;
  title: string;
  submitLabel: string;
  initial: ClientFormValues;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (values: ClientFormValues) => void;
}

const INPUT =
  "w-full rounded-control border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none transition-all duration-200";
const LABEL =
  "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-white/50";

export function ClientFormModal({
  open,
  title,
  submitLabel,
  initial,
  busy,
  error,
  onClose,
  onSubmit,
}: ClientFormModalProps) {
  const [form, setForm] = useState(initial);

  useEffect(() => {
    if (open) setForm(initial);
  }, [open, initial]);

  if (!open) return null;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="client-form-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-card border border-white/10 bg-[#0f0f0f]/95 p-6 shadow-[0_24px_64px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <div className="mb-5 flex items-start justify-between gap-3">
          <h2 id="client-form-title" className="text-lg font-semibold text-white">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-white/50 transition hover:text-white"
            aria-label="Fermer"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={LABEL}>Prénom *</span>
              <input
                required
                value={form.firstName}
                onChange={(e) =>
                  setForm((f) => ({ ...f, firstName: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Nom *</span>
              <input
                required
                value={form.lastName}
                onChange={(e) =>
                  setForm((f) => ({ ...f, lastName: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Email *</span>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Téléphone</span>
              <input
                value={form.phone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, phone: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Entreprise</span>
              <input
                value={form.company}
                onChange={(e) =>
                  setForm((f) => ({ ...f, company: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block">
              <span className={LABEL}>Site web</span>
              <input
                type="url"
                value={form.website}
                onChange={(e) =>
                  setForm((f) => ({ ...f, website: e.target.value }))
                }
                placeholder="https://…"
                className={INPUT}
              />
            </label>
            <label className="block sm:col-span-2">
              <span className={LABEL}>Adresse</span>
              <input
                value={form.address}
                onChange={(e) =>
                  setForm((f) => ({ ...f, address: e.target.value }))
                }
                className={INPUT}
              />
            </label>
            <label className="block sm:col-span-2">
              <span className={LABEL}>Notes internes</span>
              <textarea
                rows={3}
                value={form.notes}
                onChange={(e) =>
                  setForm((f) => ({ ...f, notes: e.target.value }))
                }
                className={`${INPUT} resize-y`}
              />
            </label>
            <label className="flex items-center gap-2 sm:col-span-2">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) =>
                  setForm((f) => ({ ...f, active: e.target.checked }))
                }
                className="rounded border-white/20"
              />
              <span className="text-sm text-white/70">Client actif</span>
            </label>
          </div>

          {error ? (
            <p className="rounded-control border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-control border border-white/15 px-4 py-2 text-sm text-white/70 hover:text-white"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-control border border-[#d4a843] bg-[#d4a843] px-5 py-2 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(212,168,67,0.35)] disabled:opacity-50"
            >
              {busy ? "Enregistrement…" : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
