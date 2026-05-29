import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import { AgentsSettingsPanel } from "@/components/settings/AgentsSettingsPanel";
import { GeneralSettingsPanel } from "@/components/settings/GeneralSettingsPanel";
import {
  changeMasterPassword,
  fetchSecretsStatus,
  lockSecrets,
  saveSecrets,
  unlockSecrets,
  type InfraFlags,
  type ProviderFlags,
  type SecretsStatusResponse,
  type VaultConfiguredFlags,
  type VaultKeysPayload,
} from "@/lib/secrets-api";

const PROVIDER_LABELS: { key: keyof ProviderFlags; label: string }[] = [
  { key: "deepseek", label: "DeepSeek" },
  { key: "gemini", label: "Google Gemini" },
  { key: "anthropic", label: "Anthropic" },
  { key: "openai", label: "OpenAI" },
];

const INFRA_LABELS: { key: keyof InfraFlags; label: string }[] = [
  { key: "v0", label: "v0" },
  { key: "replicate", label: "Replicate" },
  { key: "tavily", label: "Tavily" },
  { key: "railway", label: "Railway" },
  { key: "vercel", label: "Vercel" },
  { key: "github", label: "GitHub" },
];

type ApiKeyFieldDef = {
  configuredKey: keyof VaultConfiguredFlags;
  label: string;
  payloadKey: keyof VaultKeysPayload;
  emptyPlaceholder: string;
};

const LLM_API_FIELDS: ApiKeyFieldDef[] = [
  {
    configuredKey: "deepseek",
    label: "Clé API DeepSeek",
    payloadKey: "deepseek_api_key",
    emptyPlaceholder: "sk-…",
  },
  {
    configuredKey: "gemini",
    label: "Clé API Google Gemini",
    payloadKey: "google_generative_ai_api_key",
    emptyPlaceholder: "AIza…",
  },
  {
    configuredKey: "anthropic",
    label: "Clé API Anthropic",
    payloadKey: "anthropic_api_key",
    emptyPlaceholder: "sk-ant-…",
  },
  {
    configuredKey: "openai",
    label: "Clé API OpenAI (optionnel)",
    payloadKey: "openai_api_key",
    emptyPlaceholder: "sk-…",
  },
];

const INFRA_API_FIELDS: ApiKeyFieldDef[] = [
  {
    configuredKey: "v0",
    label: "V0_API_KEY",
    payloadKey: "v0_api_key",
    emptyPlaceholder: "v0_…",
  },
  {
    configuredKey: "replicate",
    label: "REPLICATE_API_KEY",
    payloadKey: "replicate_api_key",
    emptyPlaceholder: "r8_…",
  },
  {
    configuredKey: "tavily",
    label: "TAVILY_API_KEY",
    payloadKey: "tavily_api_key",
    emptyPlaceholder: "tvly-…",
  },
  {
    configuredKey: "railway",
    label: "RAILWAY_API_KEY",
    payloadKey: "railway_api_key",
    emptyPlaceholder: "…",
  },
  {
    configuredKey: "vercel",
    label: "VERCEL_TOKEN",
    payloadKey: "vercel_token",
    emptyPlaceholder: "…",
  },
  {
    configuredKey: "github",
    label: "GITHUB_TOKEN",
    payloadKey: "github_token",
    emptyPlaceholder: "ghp_…",
  },
];

const VAULT_PLACEHOLDER = "•••• (déjà en coffre)";

function ApiKeyInput({
  label,
  value,
  onChange,
  configured,
  emptyPlaceholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  configured: boolean;
  emptyPlaceholder: string;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
        {label}
      </span>
      <input
        type="password"
        autoComplete="off"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="cyber-prompt-field min-h-0 font-mono text-xs"
        placeholder={configured ? VAULT_PLACEHOLDER : emptyPlaceholder}
      />
    </label>
  );
}

function clearApiKeyInputs(
  setters: Record<keyof VaultKeysPayload, (value: string) => void>,
) {
  for (const setter of Object.values(setters)) {
    setter("");
  }
}

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
  const [v0Key, setV0Key] = useState("");
  const [replicateKey, setReplicateKey] = useState("");
  const [tavilyKey, setTavilyKey] = useState("");
  const [railwayKey, setRailwayKey] = useState("");
  const [vercelToken, setVercelToken] = useState("");
  const [githubToken, setGithubToken] = useState("");

  const keyValues: Record<keyof VaultKeysPayload, string> = {
    deepseek_api_key: deepseekKey,
    google_generative_ai_api_key: geminiKey,
    anthropic_api_key: anthropicKey,
    openai_api_key: openaiKey,
    v0_api_key: v0Key,
    replicate_api_key: replicateKey,
    tavily_api_key: tavilyKey,
    railway_api_key: railwayKey,
    vercel_token: vercelToken,
    github_token: githubToken,
  };

  const keySetters: Record<keyof VaultKeysPayload, (value: string) => void> = {
    deepseek_api_key: setDeepseekKey,
    google_generative_ai_api_key: setGeminiKey,
    anthropic_api_key: setAnthropicKey,
    openai_api_key: setOpenaiKey,
    v0_api_key: setV0Key,
    replicate_api_key: setReplicateKey,
    tavily_api_key: setTavilyKey,
    railway_api_key: setRailwayKey,
    vercel_token: setVercelToken,
    github_token: setGithubToken,
  };

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
    clearApiKeyInputs(keySetters);
    await refreshStatus();
  }

  async function handleSave() {
    if (!masterPassword.trim()) {
      setError("Le mot de passe maître est requis pour chiffrer et enregistrer.");
      return;
    }
    const keys: VaultKeysPayload = {};
    for (const [payloadKey, value] of Object.entries(keyValues) as [
      keyof VaultKeysPayload,
      string,
    ][]) {
      const trimmed = value.trim();
      if (trimmed) {
        keys[payloadKey] = trimmed;
      }
    }

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
    clearApiKeyInputs(keySetters);
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
          // configuration
        </p>
        <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">Paramètres</h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Coffre chiffré des clés API, préférences des agents et paramètres
          généraux de l&apos;application.
        </p>
      </header>

      <GeneralSettingsPanel />
      <AgentsSettingsPanel />

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
            Succès
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
            <div className="space-y-2 pt-2">
              {effective ? (
                <div className="flex flex-wrap gap-2">
                  <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                    Fournisseurs LLM actifs :
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
              <div className="flex flex-wrap gap-2">
                <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Clés infra en coffre :
                </span>
                {INFRA_LABELS.map((p) => (
                  <ProviderBadge
                    key={p.key}
                    label={p.label}
                    active={status.configured[p.key]}
                  />
                ))}
              </div>
            </div>
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
            <h2 className="text-sm font-semibold text-cyber-text">
              Clés API des modèles
            </h2>
            <p className="text-xs text-cyber-muted">
              Laissez un champ vide pour ne pas modifier cette clé. Pour une
              première configuration, renseignez au moins DeepSeek, Gemini ou
              Anthropic (CoreMindAI).
            </p>

            {LLM_API_FIELDS.map((field) => (
              <ApiKeyInput
                key={field.payloadKey}
                label={field.label}
                value={keyValues[field.payloadKey]}
                onChange={keySetters[field.payloadKey]}
                configured={status.configured[field.configuredKey]}
                emptyPlaceholder={field.emptyPlaceholder}
              />
            ))}
          </section>

          <section className="cyber-panel space-y-4 p-5">
            <h2 className="text-sm font-semibold text-cyber-text">
              Clés API infrastructure
            </h2>
            <p className="text-xs text-cyber-muted">
              Déploiement, recherche web, génération d&apos;images et intégrations
              Git. Laissez un champ vide pour ne pas modifier cette clé.
            </p>

            {INFRA_API_FIELDS.map((field) => (
              <ApiKeyInput
                key={field.payloadKey}
                label={field.label}
                value={keyValues[field.payloadKey]}
                onChange={keySetters[field.payloadKey]}
                configured={status.configured[field.configuredKey]}
                emptyPlaceholder={field.emptyPlaceholder}
              />
            ))}

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
