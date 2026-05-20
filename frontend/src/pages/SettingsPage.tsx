import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  changeMasterPassword,
  fetchSecretsStatus,
  lockSecrets,
  saveSecrets,
  unlockSecrets,
  type ProviderFlags,
  type SecretsStatusResponse,
} from "@/lib/secrets-api";

const PROVIDER_LABELS: { key: keyof ProviderFlags; label: string; field: string }[] = [
  { key: "deepseek", label: "DeepSeek", field: "deepseek_api_key" },
  { key: "gemini", label: "Google Gemini", field: "google_generative_ai_api_key" },
  { key: "anthropic", label: "Anthropic", field: "anthropic_api_key" },
  { key: "openai", label: "OpenAI", field: "openai_api_key" },
];

function PasswordFieldWithToggle({
  label,
  value,
  onChange,
  placeholder,
  autoComplete = "off",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  autoComplete?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <label className="block space-y-1">
      <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
        {label}
      </span>
      <div className="flex gap-2">
        <input
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="cyber-prompt-field min-h-0 flex-1"
          placeholder={placeholder}
        />
        <button
          type="button"
          className="cyber-action-btn shrink-0"
          onClick={() => setVisible((v) => !v)}
          aria-pressed={visible}
        >
          {visible ? "Masquer" : "Afficher"}
        </button>
      </div>
    </label>
  );
}

function ProviderBadge({ active, label }: { active: boolean; label: string }) {
  return (
    <span
      className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
        active
          ? "border-cyber-neon/40 bg-cyber-neon/10 text-cyber-neon"
          : "border-cyber-border text-cyber-muted"
      }`}
    >
      {label}
    </span>
  );
}

/**
 * Paramètres — coffre chiffré local des clés API (master password).
 */
export function SettingsPage() {
  const [status, setStatus] = useState<SecretsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [masterPassword, setMasterPassword] = useState("");
  const [oldMasterPassword, setOldMasterPassword] = useState("");
  const [newMasterPassword, setNewMasterPassword] = useState("");
  const [deepseekKey, setDeepseekKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchSecretsStatus();
      if (!response.ok || !response.data) {
        setError(
          apiErrorMessage(
            response,
            "Impossible de joindre le backend pour le coffre de clés.",
          ),
        );
        return;
      }
      setStatus(response.data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur inattendue lors du chargement du coffre.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const locked = status?.locked ?? true;
  const effective = status?.effective;

  async function handleUnlock() {
    if (!masterPassword.trim()) {
      setError("Saisissez le mot de passe maître.");
      return;
    }
    setBusy(true);
    setError(null);
    setSuccess(null);
    const response = await unlockSecrets(masterPassword);
    setBusy(false);
    if (!response.ok) {
      setError(
        apiErrorMessage(response, "Déverrouillage impossible (backend hors ligne)."),
      );
      return;
    }
    setSuccess("Coffre déverrouillé. Les clés sont actives jusqu'au verrouillage.");
    setMasterPassword("");
    await refreshStatus();
  }

  async function handleLock() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    const response = await lockSecrets();
    setBusy(false);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Verrouillage impossible."));
      return;
    }
    setSuccess("Coffre verrouillé.");
    setDeepseekKey("");
    setGeminiKey("");
    setAnthropicKey("");
    setOpenaiKey("");
    await refreshStatus();
  }

  async function handleSave() {
    if (!masterPassword.trim()) {
      setError("Le mot de passe maître est requis pour chiffrer et enregistrer.");
      return;
    }
    const keys: {
      deepseek_api_key?: string;
      google_generative_ai_api_key?: string;
      anthropic_api_key?: string;
      openai_api_key?: string;
    } = {};
    if (deepseekKey.trim()) keys.deepseek_api_key = deepseekKey.trim();
    if (geminiKey.trim()) keys.google_generative_ai_api_key = geminiKey.trim();
    if (anthropicKey.trim()) keys.anthropic_api_key = anthropicKey.trim();
    if (openaiKey.trim()) keys.openai_api_key = openaiKey.trim();

    if (Object.keys(keys).length === 0 && !status?.has_vault) {
      setError("Saisissez au moins une clé API à enregistrer.");
      return;
    }
    if (Object.keys(keys).length === 0 && status?.has_vault) {
      setError(
        "Saisissez au moins une clé à mettre à jour, ou utilisez Déverrouiller pour les clés déjà enregistrées.",
      );
      return;
    }

    setBusy(true);
    setError(null);
    setSuccess(null);
    const response = await saveSecrets(masterPassword, keys);
    setBusy(false);
    if (!response.ok) {
      setError(
        apiErrorMessage(response, "Enregistrement impossible (backend hors ligne)."),
      );
      return;
    }
    setSuccess(
      "Clés enregistrées dans le coffre chiffré local. Elles ne sont pas stockées dans backend/.env.",
    );
    setMasterPassword("");
    setDeepseekKey("");
    setGeminiKey("");
    setAnthropicKey("");
    setOpenaiKey("");
    await refreshStatus();
  }

  async function handleChangeMasterPassword() {
    if (!status?.has_vault) {
      setError("Créez d'abord un coffre en enregistrant vos clés API.");
      return;
    }
    if (!oldMasterPassword.trim() || !newMasterPassword.trim()) {
      setError("Renseignez l'ancien et le nouveau mot de passe.");
      return;
    }
    if (oldMasterPassword === newMasterPassword) {
      setError("Le nouveau mot de passe doit être différent de l'ancien.");
      return;
    }

    setBusy(true);
    setError(null);
    setSuccess(null);
    const response = await changeMasterPassword(
      oldMasterPassword,
      newMasterPassword,
    );
    setBusy(false);
    if (!response.ok) {
      setError(
        apiErrorMessage(
          response,
          "Changement de mot de passe impossible (backend hors ligne).",
        ),
      );
      return;
    }
    setSuccess(
      "Mot de passe maître mis à jour. Le coffre a été rechiffré ; utilisez le nouveau mot de passe pour déverrouiller.",
    );
    setOldMasterPassword("");
    setNewMasterPassword("");
    setMasterPassword("");
    await refreshStatus();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
          // secure_vault
        </p>
        <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">Paramètres</h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Les clés API sont chiffrées avec votre mot de passe maître et stockées
          localement sur cette machine. Le backend les charge en mémoire après
          déverrouillage.
        </p>
      </header>

      {loading ? (
        <section className="cyber-panel p-6 text-center text-sm text-cyber-neon animate-pulse">
          Chargement du coffre…
        </section>
      ) : null}

      {error ? (
        <section className="cyber-panel border-red-400/30 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-red-400">
            Erreur
          </p>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[11px] text-red-300">
            {error}
          </pre>
        </section>
      ) : null}

      {success ? (
        <section className="cyber-panel border-cyber-neon/30 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-cyber-neon">
            OK
          </p>
          <p className="mt-2 text-sm text-cyber-text">{success}</p>
        </section>
      ) : null}

      {!loading && status ? (
        <>
          <section className="cyber-panel space-y-4 p-5">
            <h2 className="text-sm font-semibold text-cyber-text">État du coffre</h2>
            <dl className="grid gap-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-cyber-muted">Fichier local</dt>
                <dd className="max-w-[60%] truncate font-mono text-[10px] text-cyber-violet">
                  {status.vault_path}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-cyber-muted">Coffre créé</dt>
                <dd className={status.has_vault ? "text-cyber-neon" : "text-cyber-muted"}>
                  {status.has_vault ? "Oui" : "Non"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-cyber-muted">Verrouillage</dt>
                <dd className={locked ? "text-amber-400" : "text-cyber-neon"}>
                  {locked ? "Verrouillé" : "Déverrouillé"}
                </dd>
              </div>
            </dl>
            {effective ? (
              <div className="flex flex-wrap gap-2 pt-2">
                <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Fournisseurs actifs :
                </span>
                {PROVIDER_LABELS.map((p) => (
                  <ProviderBadge
                    key={p.key}
                    label={p.label}
                    active={effective[p.key]}
                  />
                ))}
              </div>
            ) : null}
          </section>

          <section className="cyber-panel space-y-4 p-5">
            <h2 className="text-sm font-semibold text-cyber-text">
              Mot de passe maître
            </h2>
            <p className="text-xs text-cyber-muted">
              Utilisé pour chiffrer et déchiffrer le coffre. Ne quitte jamais cette
              machine via l&apos;API.
            </p>
            <PasswordFieldWithToggle
              label="Mot de passe"
              value={masterPassword}
              onChange={setMasterPassword}
              placeholder="Mot de passe maître"
              autoComplete="current-password"
            />
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="cyber-action-btn"
                disabled={busy || !locked}
                onClick={() => void handleUnlock()}
              >
                Déverrouiller
              </button>
              <button
                type="button"
                className="cyber-action-btn border-cyber-muted/40"
                disabled={busy || locked}
                onClick={() => void handleLock()}
              >
                Verrouiller
              </button>
            </div>
          </section>

          <section className="cyber-panel space-y-4 p-5">
            <h2 className="text-sm font-semibold text-cyber-text">
              Changer le mot de passe maître
            </h2>
            <p className="text-xs text-cyber-muted">
              Le backend déchiffre le coffre avec l&apos;ancien mot de passe, puis le
              rechiffre avec le nouveau. Vos clés API restent inchangées.
            </p>
            {!status.has_vault ? (
              <p className="text-xs text-amber-400">
                Disponible après la première enregistrement de clés dans le coffre.
              </p>
            ) : null}
            <PasswordFieldWithToggle
              label="Ancien mot de passe"
              value={oldMasterPassword}
              onChange={setOldMasterPassword}
              placeholder="Mot de passe actuel"
              autoComplete="current-password"
            />
            <PasswordFieldWithToggle
              label="Nouveau mot de passe"
              value={newMasterPassword}
              onChange={setNewMasterPassword}
              placeholder="Nouveau mot de passe maître"
              autoComplete="new-password"
            />
            <button
              type="button"
              className="cyber-action-btn cyber-action-btn-primary"
              disabled={busy || !status.has_vault}
              onClick={() => void handleChangeMasterPassword()}
            >
              Changer le mot de passe
            </button>
          </section>

          <section className="cyber-panel space-y-4 p-5">
            <h2 className="text-sm font-semibold text-cyber-text">Clés API LLM</h2>
            <p className="text-xs text-cyber-muted">
              Laissez un champ vide pour ne pas modifier cette clé. Pour une
              première configuration, renseignez au moins DeepSeek, Gemini ou
              Anthropic (CoreMindAI).
            </p>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                DeepSeek API key
              </span>
              <input
                type="password"
                autoComplete="off"
                value={deepseekKey}
                onChange={(e) => setDeepseekKey(e.target.value)}
                className="cyber-prompt-field min-h-0 font-mono text-xs"
                placeholder={status.configured.deepseek ? "•••• (déjà en coffre)" : "sk-…"}
              />
            </label>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                Google Gemini API key
              </span>
              <input
                type="password"
                autoComplete="off"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="cyber-prompt-field min-h-0 font-mono text-xs"
                placeholder={status.configured.gemini ? "•••• (déjà en coffre)" : "AIza…"}
              />
            </label>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                Anthropic API key
              </span>
              <input
                type="password"
                autoComplete="off"
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                className="cyber-prompt-field min-h-0 font-mono text-xs"
                placeholder={status.configured.anthropic ? "•••• (déjà en coffre)" : "sk-ant-…"}
              />
            </label>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                OpenAI API key (optionnel)
              </span>
              <input
                type="password"
                autoComplete="off"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                className="cyber-prompt-field min-h-0 font-mono text-xs"
                placeholder={status.configured.openai ? "•••• (déjà en coffre)" : "sk-…"}
              />
            </label>

            <button
              type="button"
              className="cyber-action-btn w-full sm:w-auto"
              disabled={busy}
              onClick={() => void handleSave()}
            >
              Enregistrer dans le coffre chiffré
            </button>
          </section>
        </>
      ) : null}
    </div>
  );
}
