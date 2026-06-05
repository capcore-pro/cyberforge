import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  GLASS_SECTION,
  GOLD_BTN,
  INPUT,
  LABEL,
} from "@/components/settings/settings-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import { uploadMediaAsset, fetchMediaAsset } from "@/lib/media-api";
import {
  fetchProfileSettings,
  saveProfileSettings,
  type ProfileSettings,
} from "@/lib/settings-api";
import { setUserFirstName } from "@/lib/user-preferences";

function profileInitials(first: string, last: string): string {
  const a = first.trim()[0] ?? "";
  const b = last.trim()[0] ?? "";
  if (a && b) return `${a}${b}`.toUpperCase();
  return (a || b || "MG").toUpperCase().slice(0, 2);
}

export function ProfileSettingsPanel() {
  const [form, setForm] = useState<ProfileSettings>({
    first_name: "Mat",
    last_name: "",
    title: "Fondateur CapCore",
    email: "",
    phone: "",
    siret: "",
    vat_number: "",
    address_street: "",
    address_postal_code: "",
    address_city: "",
    signature: "",
    kbis_media_id: null,
  });
  const [kbisName, setKbisName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const initials = useMemo(
    () => profileInitials(form.first_name, form.last_name),
    [form.first_name, form.last_name],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchProfileSettings();
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Impossible de charger le profil."));
      setLoading(false);
      return;
    }
    setForm(res.data);
    if (res.data.kbis_media_id) {
      const asset = await fetchMediaAsset(res.data.kbis_media_id);
      if (asset.ok && asset.data) setKbisName(asset.data.filename);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!form.first_name.trim()) {
      setError("Le prénom est obligatoire.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    setUserFirstName(form.first_name.trim());
    const res = await saveProfileSettings(form);
    setSaving(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Enregistrement impossible."));
      return;
    }
    if (res.data) setForm(res.data);
    setSuccess("Profil enregistré.");
  }

  async function handleKbisUpload(file: File) {
    setUploading(true);
    setError(null);
    const res = await uploadMediaAsset(file, { tags: "kbis,legal,capcore" });
    setUploading(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Échec de l'upload KBIS."));
      return;
    }
    setForm((f) => ({ ...f, kbis_media_id: res.data!.id }));
    setKbisName(res.data.filename);
    setSuccess("KBIS ajouté — enregistrez le profil pour confirmer.");
  }

  if (loading) {
    return (
      <p className="animate-pulse text-sm text-white/50">Chargement du profil…</p>
    );
  }

  return (
    <div className="space-y-6">
      <div className={GLASS_SECTION}>
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Avatar
        </h3>
        <div className="flex flex-wrap items-center gap-4">
          <div
            className="flex h-20 w-20 items-center justify-center rounded-full border border-[#d4a843]/40 bg-[#0a0a0a] text-2xl font-bold text-[#d4a843]"
            aria-hidden
          >
            {initials}
          </div>
          <button
            type="button"
            disabled
            className="rounded-control border border-white/15 px-4 py-2 text-sm text-white/40"
            title="Bientôt disponible"
          >
            Changer la photo
          </button>
        </div>
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Informations personnelles
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label>
            <span className={LABEL}>Prénom *</span>
            <input
              required
              value={form.first_name}
              onChange={(e) =>
                setForm((f) => ({ ...f, first_name: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Nom</span>
            <input
              value={form.last_name}
              onChange={(e) =>
                setForm((f) => ({ ...f, last_name: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Titre</span>
            <input
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({ ...f, title: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Email CapCore</span>
            <input
              type="email"
              value={form.email}
              onChange={(e) =>
                setForm((f) => ({ ...f, email: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label className="sm:col-span-2">
            <span className={LABEL}>Téléphone</span>
            <input
              value={form.phone}
              onChange={(e) =>
                setForm((f) => ({ ...f, phone: e.target.value }))
              }
              className={INPUT}
            />
          </label>
        </div>
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Informations légales
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label>
            <span className={LABEL}>SIRET</span>
            <input
              inputMode="numeric"
              value={form.siret}
              onChange={(e) =>
                setForm((f) => ({ ...f, siret: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Numéro TVA</span>
            <input
              value={form.vat_number}
              onChange={(e) =>
                setForm((f) => ({ ...f, vat_number: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label className="sm:col-span-2">
            <span className={LABEL}>Rue</span>
            <input
              value={form.address_street}
              onChange={(e) =>
                setForm((f) => ({ ...f, address_street: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Code postal</span>
            <input
              value={form.address_postal_code}
              onChange={(e) =>
                setForm((f) => ({ ...f, address_postal_code: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <label>
            <span className={LABEL}>Ville</span>
            <input
              value={form.address_city}
              onChange={(e) =>
                setForm((f) => ({ ...f, address_city: e.target.value }))
              }
              className={INPUT}
            />
          </label>
          <div className="sm:col-span-2">
            <span className={LABEL}>KBIS</span>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleKbisUpload(file);
                e.target.value = "";
              }}
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                className="rounded-control border border-[#d4a843]/40 bg-[#d4a843]/10 px-4 py-2 text-sm text-[#d4a843] hover:border-[#d4a843] disabled:opacity-50"
              >
                {uploading ? "Upload…" : "Uploader mon KBIS"}
              </button>
              <span className="text-sm text-white/50">
                {kbisName ?? "Aucun document"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Signature
        </h3>
        <label>
          <span className={LABEL}>Signature pour devis / factures / contrats</span>
          <textarea
            rows={4}
            value={form.signature}
            onChange={(e) =>
              setForm((f) => ({ ...f, signature: e.target.value }))
            }
            className={`${INPUT} resize-y`}
          />
        </label>
        {form.signature.trim() ? (
          <div className="mt-4 rounded-control border border-white/10 bg-black/30 px-4 py-3">
            <p className="mb-1 text-[10px] uppercase tracking-wide text-white/35">
              Aperçu
            </p>
            <p className="whitespace-pre-wrap font-serif text-sm italic text-white/80">
              {form.signature}
            </p>
          </div>
        ) : null}
      </div>

      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="rounded-control border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-[#d4a843]">
          {success}
        </p>
      ) : null}

      <button
        type="button"
        disabled={saving}
        onClick={() => void handleSave()}
        className={GOLD_BTN}
      >
        💾 {saving ? "Enregistrement…" : "Enregistrer le profil"}
      </button>
    </div>
  );
}
