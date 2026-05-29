import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import { uploadMediaAsset, fetchMediaAsset } from "@/lib/media-api";
import {
  fetchProfileSettings,
  saveProfileSettings,
} from "@/lib/settings-api";
import { getUserFirstName, setUserFirstName } from "@/lib/user-preferences";

export function ProfileSettingsPanel() {
  const [firstName, setFirstName] = useState(() => getUserFirstName());
  const [email, setEmail] = useState("");
  const [siret, setSiret] = useState("");
  const [kbisName, setKbisName] = useState<string | null>(null);
  const [kbisMediaId, setKbisMediaId] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchProfileSettings();
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Impossible de charger le profil."));
      setLoading(false);
      return;
    }
    setEmail(res.data.email);
    setSiret(res.data.siret);
    setKbisMediaId(res.data.kbis_media_id);
    if (res.data.kbis_media_id) {
      const asset = await fetchMediaAsset(res.data.kbis_media_id);
      if (asset.ok && asset.data) {
        setKbisName(asset.data.filename);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    setUserFirstName(firstName);
    const res = await saveProfileSettings({
      email: email.trim(),
      siret: siret.trim(),
      kbis_media_id: kbisMediaId,
    });
    setSaving(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Enregistrement impossible."));
      return;
    }
    setSuccess("Profil enregistré (local + backend/.env).");
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
    setKbisMediaId(res.data.id);
    setKbisName(res.data.filename);
    setSuccess("KBIS ajouté à la médiathèque. Enregistrez pour lier au profil.");
  }

  if (loading) {
    return (
      <p className="animate-pulse text-sm text-cf-muted">Chargement du profil…</p>
    );
  }

  return (
    <div className="space-y-6">
      <label className="block">
        <span className="cf-section-label mb-2 block">Prénom</span>
        <input
          type="text"
          className="w-full max-w-md rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="Mat"
        />
        <p className="mt-1 text-[11px] text-cf-muted">
          Affiché dans « Bonjour … » sur le tableau de bord.
        </p>
      </label>

      <label className="block">
        <span className="cf-section-label mb-2 block">Email CapCore</span>
        <input
          type="email"
          className="w-full max-w-md rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="capcore.pro@gmail.com"
        />
      </label>

      <label className="block">
        <span className="cf-section-label mb-2 block">SIRET</span>
        <input
          type="text"
          inputMode="numeric"
          className="w-full max-w-md rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
          value={siret}
          onChange={(e) => setSiret(e.target.value)}
          placeholder="12345678901234"
        />
        <p className="mt-1 text-[11px] text-cf-muted">
          Utilisé dans les PDFs légaux (variable MAT_SIRET).
        </p>
      </label>

      <div>
        <span className="cf-section-label mb-2 block">KBIS</span>
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
            className="rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-sm text-cf-gold hover:border-cf-gold disabled:opacity-50"
          >
            {uploading ? "Upload…" : "Uploader mon KBIS"}
          </button>
          {kbisName ? (
            <span className="text-sm text-cf-muted">{kbisName}</span>
          ) : (
            <span className="text-sm text-cf-tertiary">Aucun document</span>
          )}
        </div>
        <p className="mt-1 text-[11px] text-cf-muted">
          Stocké dans la médiathèque (tag kbis).
        </p>
      </div>

      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="rounded-control border border-cf-gold/30 bg-cf-active px-4 py-3 text-sm text-cf-gold">
          {success}
        </p>
      ) : null}

      <button
        type="button"
        disabled={saving}
        onClick={() => void handleSave()}
        className="rounded-control border border-cf-gold bg-cf-gold px-6 py-2.5 text-sm font-medium text-cf-main hover:bg-cf-gold-hover disabled:opacity-50"
      >
        {saving ? "Enregistrement…" : "Enregistrer le profil"}
      </button>
    </div>
  );
}
