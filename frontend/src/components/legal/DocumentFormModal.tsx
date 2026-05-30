import { useEffect, useMemo, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createLegalClient,
  type LegalClient,
  type LegalDocument,
  type LineItemInput,
} from "@/lib/legal-api";

export interface LineDraft {
  key: string;
  description: string;
  quantity: number;
  unit_price: number;
}

function newLine(): LineDraft {
  return {
    key: crypto.randomUUID(),
    description: "",
    quantity: 1,
    unit_price: 0,
  };
}

function linesFromDoc(doc: LegalDocument | null): LineDraft[] {
  if (!doc?.line_items?.length) return [newLine()];
  return doc.line_items.map((l) => ({
    key: l.id,
    description: l.description,
    quantity: l.quantity,
    unit_price: l.unit_price,
  }));
}

export interface DocumentFormValues {
  title: string;
  client_id: string | null;
  notes: string;
  lines: LineItemInput[];
  total_ht: number;
}

export function DocumentFormModal({
  open,
  mode,
  docTypeLabel,
  initial,
  clients,
  onClientCreated,
  onClose,
  onSubmit,
  busy,
  error,
}: {
  open: boolean;
  mode: "create" | "edit";
  docTypeLabel: string;
  initial: LegalDocument | null;
  clients: LegalClient[];
  onClientCreated?: () => void;
  onClose: () => void;
  onSubmit: (values: DocumentFormValues) => void | Promise<void>;
  busy: boolean;
  error: string | null;
}) {
  const [title, setTitle] = useState("");
  const [clientId, setClientId] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);
  const [showNewClient, setShowNewClient] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [newClientEmail, setNewClientEmail] = useState("");
  const [newClientBusy, setNewClientBusy] = useState(false);
  const [newClientError, setNewClientError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTitle(initial?.title ?? "");
    setClientId(initial?.client_id ?? "");
    setNotes(initial?.notes ?? "");
    setLines(linesFromDoc(initial));
    setShowNewClient(false);
    setNewClientName("");
    setNewClientEmail("");
  }, [open, initial]);

  const totalHt = useMemo(
    () =>
      lines.reduce(
        (sum, l) => sum + Math.max(0, l.quantity) * Math.max(0, l.unit_price),
        0,
      ),
    [lines],
  );

  if (!open) return null;

  function updateLine(key: string, patch: Partial<LineDraft>) {
    setLines((prev) =>
      prev.map((l) => (l.key === key ? { ...l, ...patch } : l)),
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validLines = lines
      .filter((l) => l.description.trim())
      .map((l, idx) => ({
        description: l.description.trim(),
        quantity: l.quantity,
        unit_price: l.unit_price,
        order: idx,
      }));
    onSubmit({
      title: title.trim(),
      client_id: clientId || null,
      notes: notes.trim(),
      lines: validLines.length ? validLines : [{ description: "Prestation", quantity: 1, unit_price: 0 }],
      total_ht: totalHt,
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/80 p-4"
      role="dialog"
      aria-modal
    >
      <form
        onSubmit={handleSubmit}
        className="cyber-panel my-4 flex max-h-[92vh] w-full max-w-3xl flex-col border-cyber-neon/30"
      >
        <div className="border-b border-cyber-border px-5 py-4">
          <BackButton className="mb-3" onClick={onClose} />
          <h2 className="text-lg font-semibold text-cyber-text">
            {mode === "create" ? `Nouveau ${docTypeLabel.toLowerCase()}` : `Modifier ${docTypeLabel.toLowerCase()}`}
          </h2>
          {initial?.number ? (
            <p className="mt-1 text-xs text-cyber-muted">{initial.number}</p>
          ) : null}
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {error ? (
            <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-cyber-muted">
              Client
            </label>
            <div className="flex flex-wrap gap-2">
              <select
                className="cyber-input min-w-[200px] flex-1"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
              >
                <option value="">— Sélectionner un client —</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email})
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="cyber-action-btn text-xs"
                onClick={() => setShowNewClient((v) => !v)}
              >
                + Client
              </button>
            </div>
            {showNewClient ? (
              <div className="mt-2 space-y-2 rounded border border-cyber-border bg-cyber-bg/50 p-3">
                <div className="grid gap-2 sm:grid-cols-2">
                  <input
                    className="cyber-input"
                    placeholder="Nom ou raison sociale *"
                    value={newClientName}
                    onChange={(e) => setNewClientName(e.target.value)}
                  />
                  <input
                    className="cyber-input"
                    type="email"
                    placeholder="Email *"
                    value={newClientEmail}
                    onChange={(e) => setNewClientEmail(e.target.value)}
                  />
                </div>
                {newClientError ? (
                  <p className="text-xs text-red-300">{newClientError}</p>
                ) : null}
                <button
                  type="button"
                  className="cyber-action-btn text-xs"
                  disabled={
                    newClientBusy ||
                    !newClientName.trim() ||
                    !newClientEmail.trim()
                  }
                  onClick={async () => {
                    setNewClientBusy(true);
                    setNewClientError(null);
                    const res = await createLegalClient({
                      name: newClientName.trim(),
                      email: newClientEmail.trim(),
                    });
                    setNewClientBusy(false);
                    if (!res.ok) {
                      setNewClientError(
                        apiErrorMessage(res, "Création client impossible."),
                      );
                      return;
                    }
                    if (res.data) {
                      setClientId(res.data.id);
                      setShowNewClient(false);
                      onClientCreated?.();
                    }
                  }}
                >
                  {newClientBusy ? "Création…" : "Créer et sélectionner"}
                </button>
              </div>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-cyber-muted">
              Titre
            </label>
            <input
              className="cyber-input w-full"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-cyber-muted">
                Lignes
              </span>
              <button
                type="button"
                className="cyber-action-btn text-xs"
                onClick={() => setLines((prev) => [...prev, newLine()])}
              >
                + Ligne
              </button>
            </div>
            <div className="space-y-2">
              {lines.map((line) => (
                <div
                  key={line.key}
                  className="grid gap-2 rounded border border-cyber-border bg-cyber-bg/40 p-2 sm:grid-cols-[1fr_72px_100px_32px]"
                >
                  <input
                    className="cyber-input text-sm"
                    placeholder="Description"
                    value={line.description}
                    onChange={(e) =>
                      updateLine(line.key, { description: e.target.value })
                    }
                  />
                  <input
                    className="cyber-input text-sm"
                    type="number"
                    min={0}
                    step="any"
                    placeholder="Qté"
                    value={line.quantity}
                    onChange={(e) =>
                      updateLine(line.key, {
                        quantity: Number(e.target.value) || 0,
                      })
                    }
                  />
                  <input
                    className="cyber-input text-sm"
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Prix HT"
                    value={line.unit_price}
                    onChange={(e) =>
                      updateLine(line.key, {
                        unit_price: Number(e.target.value) || 0,
                      })
                    }
                  />
                  <button
                    type="button"
                    className="cyber-action-btn px-2 text-red-300"
                    title="Supprimer la ligne"
                    disabled={lines.length <= 1}
                    onClick={() =>
                      setLines((prev) =>
                        prev.length <= 1
                          ? prev
                          : prev.filter((l) => l.key !== line.key),
                      )
                    }
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded border border-cyber-border bg-cyber-surface/60 px-4 py-3">
            <div className="flex justify-between text-sm">
              <span className="text-cyber-muted">Total HT</span>
              <span className="font-mono font-semibold text-cyber-neon">
                {formatEur(totalHt)}
              </span>
            </div>
            <p className="mt-2 text-[11px] text-cyber-muted">
              TVA non applicable — article 293 B du CGI (micro-entrepreneur)
            </p>
            <div className="mt-1 flex justify-between text-sm">
              <span className="text-cyber-muted">Total TTC</span>
              <span className="font-mono text-cyber-text">{formatEur(totalHt)}</span>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-cyber-muted">
              Notes (optionnel)
            </label>
            <textarea
              className="cyber-input min-h-[72px] w-full resize-y"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-cyber-border px-5 py-4">
          <button
            type="button"
            className="cyber-action-btn"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button
            type="submit"
            className="cyber-action-btn cyber-action-btn-primary"
            disabled={busy || !title.trim()}
          >
            {busy ? "Enregistrement…" : mode === "create" ? "Créer" : "Enregistrer"}
          </button>
        </div>
      </form>
    </div>
  );
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}
