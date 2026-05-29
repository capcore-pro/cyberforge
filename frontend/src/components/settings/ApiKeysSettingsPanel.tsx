import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchSecretsStatus,
  saveSecrets,
  testSecretKey,
  unlockSecrets,
  type SecretsStatusResponse,
  type VaultConfiguredFlags,
  type VaultKeysPayload,
} from "@/lib/secrets-api";

type ApiKeyId = keyof VaultConfiguredFlags;

interface ApiKeyDef {
  id: ApiKeyId;
  label: string;
  payloadKey: keyof VaultKeysPayload;
  placeholder: string;
}

const API_KEYS: ApiKeyDef[] = [
  {
    id: "anthropic",
    label: "Anthropic",
    payloadKey: "anthropic_api_key",
    placeholder: "sk-ant-…",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    payloadKey: "deepseek_api_key",
    placeholder: "sk-…",
  },
  { id: "v0", label: "v0", payloadKey: "v0_api_key", placeholder: "v0_…" },
  {
    id: "replicate",
    label: "Replicate",
    payloadKey: "replicate_api_key",
    placeholder: "r8_…",
  },
  {
    id: "tavily",
    label: "Tavily",
    payloadKey: "tavily_api_key",
    placeholder: "tvly-…",
  },
  {
    id: "railway",
    label: "Railway",
    payloadKey: "railway_api_key",
    placeholder: "…",
  },
  {
    id: "vercel",
    label: "Vercel",
    payloadKey: "vercel_token",
    placeholder: "…",
  },
  {
    id: "github",
    label: "GitHub",
    payloadKey: "github_token",
    placeholder: "ghp_…",
  },
  {
    id: "brevo",
    label: "Brevo",
    payloadKey: "brevo_api_key",
    placeholder: "xkeysib-…",
  },
  {
    id: "stripe",
    label: "Stripe",
    payloadKey: "stripe_secret_key",
    placeholder: "sk_live_…",
  },
];

const VAULT_MASK = "••••••••••••";

function ApiKeyRow({
  def,
  configured,
  value,
  onChange,
  onTest,
  testResult,
  testing,
}: {
  def: ApiKeyDef;
  configured: boolean;
  value: string;
  onChange: (v: string) => void;
  onTest: () => void;
  testResult: { valid: boolean; message: string } | null;
  testing: boolean;
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-cf-text">{def.label}</span>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
            configured
              ? "border-cf-gold/40 bg-cf-active text-cf-gold"
              : "border-red-500/40 bg-red-950/30 text-red-300"
          }`}
        >
          {configured ? "Configurée" : "Manquante"}
        </span>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          type={visible ? "text" : "password"}
          autoComplete="off"
          value={value || (!visible && configured ? VAULT_MASK : value)}
          onChange={(e) => {
            const next = e.target.value;
            if (next === VAULT_MASK) return;
            onChange(next);
          }}
          onFocus={() => {
            if (!value && configured) onChange("");
          }}
          placeholder={configured ? "Laisser vide pour conserver" : def.placeholder}
          className="min-w-0 flex-1 rounded-control border border-cf-border-input bg-cf-card px-3 py-2 font-mono text-xs text-cf-text focus:border-cf-gold/50 focus:outline-none"
        />
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="rounded-control border border-cf-border-input px-3 py-2 text-xs text-cf-muted hover:text-cf-text"
            aria-label={visible ? "Masquer" : "Révéler"}
          >
            {visible ? "Masquer" : "Révéler"}
          </button>
          <button
            type="button"
            disabled={testing}
            onClick={onTest}
            className="rounded-control border border-cf-border-input px-3 py-2 text-xs text-cf-gold hover:border-cf-gold/50 disabled:opacity-50"
          >
            {testing ? "Test…" : "Tester"}
          </button>
        </div>
      </div>

      {testResult ? (
        <p
          className={`mt-2 text-xs ${
            testResult.valid ? "text-cf-success" : "text-red-300"
          }`}
        >
          {testResult.valid ? "✅ Valide" : "❌ Invalide"} — {testResult.message}
        </p>
      ) : null}
    </div>
  );
}

export function ApiKeysSettingsPanel() {
  const [status, setStatus] = useState<SecretsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [vaultPassword, setVaultPassword] = useState("");
  const [unlocked, setUnlocked] = useState(false);

  const [values, setValues] = useState<Record<keyof VaultKeysPayload, string>>({
    anthropic_api_key: "",
    deepseek_api_key: "",
    v0_api_key: "",
    replicate_api_key: "",
    tavily_api_key: "",
    railway_api_key: "",
    vercel_token: "",
    github_token: "",
    brevo_api_key: "",
    stripe_secret_key: "",
    openai_api_key: "",
    google_generative_ai_api_key: "",
  });

  const [testResults, setTestResults] = useState<
    Partial<Record<ApiKeyId, { valid: boolean; message: string }>>
  >({});
  const [testingId, setTestingId] = useState<ApiKeyId | null>(null);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    const res = await fetchSecretsStatus();
    if (res.ok && res.data) setStatus(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  async function handleUnlock() {
    if (!vaultPassword.trim()) {
      setError("Saisissez le mot de passe du coffre.");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await unlockSecrets(vaultPassword);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Mot de passe incorrect ou backend indisponible."));
      setUnlocked(false);
      return;
    }
    setUnlocked(true);
    setSuccess("Coffre déverrouillé.");
    await refreshStatus();
  }

  async function handleTest(def: ApiKeyDef) {
    setTestingId(def.id);
    setError(null);
    const res = await testSecretKey(
      def.id,
      values[def.payloadKey]?.trim() || undefined,
    );
    setTestingId(null);
    if (!res.ok || !res.data) {
      setTestResults((prev) => ({
        ...prev,
        [def.id]: { valid: false, message: apiErrorMessage(res, "Test impossible.") },
      }));
      return;
    }
    setTestResults((prev) => ({
      ...prev,
      [def.id]: { valid: res.data!.valid, message: res.data!.message },
    }));
  }

  async function handleSaveAll() {
    if (!vaultPassword.trim()) {
      setError("Mot de passe du coffre requis pour enregistrer.");
      return;
    }
    const keys: VaultKeysPayload = {};
    for (const def of API_KEYS) {
      const trimmed = values[def.payloadKey]?.trim();
      if (trimmed) keys[def.payloadKey] = trimmed;
    }
    if (Object.keys(keys).length === 0 && !status?.has_vault) {
      setError("Saisissez au moins une clé à enregistrer.");
      return;
    }

    setBusy(true);
    setError(null);
    setSuccess(null);
    const res = await saveSecrets(vaultPassword, keys);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Enregistrement impossible."));
      return;
    }
    setSuccess("Toutes les clés ont été enregistrées dans le coffre.");
    setValues((prev) => {
      const cleared = { ...prev };
      for (const def of API_KEYS) cleared[def.payloadKey] = "";
      return cleared;
    });
    await refreshStatus();
  }

  if (loading) {
    return <p className="animate-pulse text-sm text-cf-muted">Chargement des clés…</p>;
  }

  const configured = status?.configured ?? ({} as VaultConfiguredFlags);

  return (
    <div className="space-y-6">
      <div className="rounded-card border border-cf-border-input bg-cf-secondary/30 p-4">
        <label className="block">
          <span className="cf-section-label mb-2 block">Mot de passe du coffre</span>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="password"
              autoComplete="current-password"
              value={vaultPassword}
              onChange={(e) => setVaultPassword(e.target.value)}
              placeholder="Mot de passe pour chiffrer / déverrouiller"
              className="min-w-0 flex-1 rounded-control border border-cf-border-input bg-cf-card px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
            />
            <button
              type="button"
              disabled={busy || unlocked}
              onClick={() => void handleUnlock()}
              className="rounded-control border border-cf-border-input px-4 py-2 text-sm text-cf-muted hover:text-cf-text disabled:opacity-50"
            >
              Déverrouiller
            </button>
          </div>
        </label>
        {status ? (
          <p className="mt-2 text-[11px] text-cf-muted">
            Coffre {status.has_vault ? "actif" : "non créé"} —{" "}
            {status.locked ? "verrouillé" : "déverrouillé"}
          </p>
        ) : null}
      </div>

      <div className="space-y-3">
        {API_KEYS.map((def) => (
          <ApiKeyRow
            key={def.id}
            def={def}
            configured={Boolean(configured[def.id])}
            value={values[def.payloadKey]}
            onChange={(v) =>
              setValues((prev) => ({ ...prev, [def.payloadKey]: v }))
            }
            onTest={() => void handleTest(def)}
            testResult={testResults[def.id] ?? null}
            testing={testingId === def.id}
          />
        ))}
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
        disabled={busy}
        onClick={() => void handleSaveAll()}
        className="w-full rounded-control border border-cf-gold bg-cf-gold py-3 text-sm font-semibold text-cf-main hover:bg-cf-gold-hover disabled:opacity-50 sm:w-auto sm:px-10"
      >
        {busy ? "Enregistrement…" : "Enregistrer toutes les clés"}
      </button>
    </div>
  );
}
