import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createLegalClient,
  deleteLegalClient,
  fetchLegalClients,
  updateLegalClient,
  type LegalClient,
} from "@/lib/legal-api";

const emptyForm = {
  name: "",
  email: "",
  phone: "",
  address: "",
  siret: "",
};

export function LegalClientsPanel() {
  const [clients, setClients] = useState<LegalClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchLegalClients();
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de charger les clients."));
      setLoading(false);
      return;
    }
    setClients(Array.isArray(res.data) ? res.data : []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function startEdit(client: LegalClient) {
    setEditingId(client.id);
    setForm({
      name: client.name,
      email: client.email,
      phone: client.phone ?? "",
      address: client.address ?? "",
      siret: client.siret ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) return;
    setBusy(true);
    setError(null);
    const body = {
      name: form.name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      siret: form.siret.trim() || null,
    };
    const res = editingId
      ? await updateLegalClient(editingId, body)
      : await createLegalClient(body);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Enregistrement impossible."));
      return;
    }
    cancelEdit();
    await load();
  }

  async function handleDelete(client: LegalClient) {
    if (
      !window.confirm(
        `Supprimer le client « ${client.name} » ? Les documents associés conserveront une référence vide.`,
      )
    ) {
      return;
    }
    const res = await deleteLegalClient(client.id);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Suppression impossible."));
      return;
    }
    if (editingId === client.id) cancelEdit();
    await load();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-muted">
            Carnet clients
          </h3>
          <button
            type="button"
            className="cyber-action-btn text-xs"
            onClick={() => void load()}
          >
            Actualiser
          </button>
        </div>
        {error ? (
          <p className="mb-3 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
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
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">SIRET</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {clients.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-8 text-center text-cyber-muted">
                      Aucun client enregistré.
                    </td>
                  </tr>
                ) : (
                  clients.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                    >
                      <td className="px-3 py-2 font-medium text-cyber-text">
                        {c.name}
                      </td>
                      <td className="px-3 py-2 text-cyber-muted">{c.email}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {c.siret || "—"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <button
                            type="button"
                            className="cyber-action-btn text-[10px]"
                            onClick={() => startEdit(c)}
                          >
                            Modifier
                          </button>
                          <button
                            type="button"
                            className="cyber-action-btn text-[10px] text-red-300"
                            onClick={() => void handleDelete(c)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="cyber-panel h-fit space-y-3 border-cyber-border p-4"
      >
        <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-neon">
          {editingId ? "Modifier le client" : "Nouveau client"}
        </h3>
        <input
          className="cyber-input w-full"
          placeholder="Nom ou raison sociale *"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          required
        />
        <input
          className="cyber-input w-full"
          type="email"
          placeholder="Email *"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          required
        />
        <input
          className="cyber-input w-full"
          placeholder="Téléphone"
          value={form.phone}
          onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
        />
        <input
          className="cyber-input w-full"
          placeholder="Adresse"
          value={form.address}
          onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
        />
        <input
          className="cyber-input w-full"
          placeholder="SIRET"
          value={form.siret}
          onChange={(e) => setForm((f) => ({ ...f, siret: e.target.value }))}
        />
        <div className="flex gap-2 pt-1">
          <button
            type="submit"
            className="cyber-action-btn cyber-action-btn-primary flex-1 text-xs"
            disabled={busy}
          >
            {busy ? "…" : editingId ? "Enregistrer" : "Ajouter"}
          </button>
          {editingId ? (
            <button
              type="button"
              className="cyber-action-btn text-xs"
              onClick={cancelEdit}
            >
              Annuler
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
}
