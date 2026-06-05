import { useCallback, useEffect, useState } from "react";
import { Users } from "lucide-react";
import { BackButton } from "@/components/BackButton";
import {
  GLASS_BTN,
  FORM_CONTAINER,
  GLASS_SECTION,
  GOLD_BTN,
  INPUT,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { AccountingToast } from "@/components/accounting/AccountingToast";
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
  const [toast, setToast] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await fetchLegalClients();
    if (!res.ok) {
      const msg = apiErrorMessage(res, "Impossible de charger les clients.");
      logAccountingApiError("Carnet clients", msg);
      setClients([]);
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
      const msg = apiErrorMessage(res, "Enregistrement impossible.");
      if (!shouldSilenceApiError(msg)) setToast(msg);
      else logAccountingApiError("Client save", msg);
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
      const msg = apiErrorMessage(res, "Suppression impossible.");
      if (!shouldSilenceApiError(msg)) setToast(msg);
      return;
    }
    if (editingId === client.id) cancelEdit();
    await load();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className={GLASS_SECTION}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
            Carnet clients
          </h3>
          <button type="button" onClick={() => void load()} className={GLASS_BTN}>
            Actualiser
          </button>
        </div>
        {loading ? (
          <p className="animate-pulse text-sm text-white/50">Chargement…</p>
        ) : clients.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Users className="mb-3 h-10 w-10 text-white/20" aria-hidden />
            <p className="text-sm text-white/30">Aucun client enregistré</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-widest text-white/40">
                  <th className="px-3 py-3 font-medium">Nom</th>
                  <th className="px-3 py-3 font-medium">Email</th>
                  <th className="px-3 py-3 font-medium">SIRET</th>
                  <th className="px-3 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-white/5 transition hover:bg-white/5"
                  >
                    <td className="px-3 py-3 font-medium text-white">{c.name}</td>
                    <td className="px-3 py-3 text-white/50">{c.email}</td>
                    <td className="px-3 py-3 font-mono text-xs text-white/60">
                      {c.siret || "—"}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className={GLASS_BTN}
                          onClick={() => startEdit(c)}
                        >
                          Modifier
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-red-500/30 px-2 py-1 text-[10px] text-red-300 hover:bg-red-950/30"
                          onClick={() => void handleDelete(c)}
                        >
                          Supprimer
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className={`${FORM_CONTAINER} h-fit space-y-3`}>
        {editingId ? (
          <BackButton className="mb-1" onClick={cancelEdit} />
        ) : null}
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
          {editingId ? "Modifier le client" : "Nouveau client"}
        </h3>
        <input
          className={INPUT}
          placeholder="Nom ou raison sociale *"
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
          placeholder="Téléphone"
          value={form.phone}
          onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
        />
        <input
          className={INPUT}
          placeholder="Adresse"
          value={form.address}
          onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
        />
        <input
          className={INPUT}
          placeholder="SIRET"
          value={form.siret}
          onChange={(e) => setForm((f) => ({ ...f, siret: e.target.value }))}
        />
        <div className="flex gap-2 pt-1">
          <button type="submit" className={`${GOLD_BTN} w-full`} disabled={busy}>
            {busy ? "…" : editingId ? "Enregistrer" : "Ajouter"}
          </button>
          {editingId ? (
            <button type="button" className={GLASS_BTN} onClick={cancelEdit}>
              Annuler
            </button>
          ) : null}
        </div>
      </form>

      <AccountingToast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
