import { useCallback, useEffect, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchSecretsStatus,
  saveSecrets,
  testSecretKey,
  type SecretsStatusResponse,
} from "@/lib/secrets-api";
import {
  isResearchEnabled,
  setResearchEnabled,
} from "@/lib/research-preferences";

const VAULT_MASK = "••••••••••••";

function ResearchToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative h-7 w-12 shrink-0 rounded-full border transition ${
        enabled
          ? "border-cf-gold bg-cf-gold"
          : "border-cf-border-input bg-cf-tertiary/40"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-cf-main transition ${
          enabled ? "left-[22px]" : "left-0.5"
        }`}
      />
    </button>
  );
}

interface KeyFieldProps {
  label: string;
  configured: boolean;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
  onTest: () => void;
  testing: boolean;
  testMessage: string | null;
  testValid: boolean | null;
}

function KeyField({
  label,
  configured,
  value,
  placeholder,
  onChange,
  onTest,
  testing,
  testMessage,
  testValid,
}: KeyFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="rounded-card border border-cf-border-input bg-cf-secondary/30 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium text-cf-text">{label}</span>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
            configured
              ? "border-cf-gold/40 text-cf-gold"
              : "border-red-500/40 text-red-300"
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
            if (e.target.value === VAULT_MASK) return;
            onChange(e.target.value);
          }}
          onFocus={() => {
            if (!value && configured) onChange("");
          }}
          placeholder={configured ? "Laisser vide pour conserver" : placeholder}
          className="min-w-0 flex-1 rounded-control border border-cf-border-input bg-cf-card px-3 py-2 font-mono text-xs text-cf-text focus:border-cf-gold/50 focus:outline-none"
        />
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="rounded-control border border-cf-border-input px-2 py-1.5 text-xs text-cf-muted"
          >
            {visible ? "Masquer" : "Révéler"}
          </button>
          <button
            type="button"
            disabled={testing}
            onClick={onTest}
            className="rounded-control border border-cf-border-input px-2 py-1.5 text-xs text-cf-gold disabled:opacity-50"
          >
            {testing ? "Test…" : "Tester"}
          </button>
        </div>
      </div>
      {testMessage ? (
        <p
          className={`mt-2 text-[11px] ${
            testValid ? "text-cf-success" : "text-red-300"
          }`}
        >
          {testValid ? "✅" : "❌"} {testMessage}
        </p>
      ) : null}
    </div>
  );
}

/** Section Recherche — toggle + clés Brave Search et Exa AI. */
export function ResearchSettingsPanel() {
  const [enabled, setEnabled] = useState(isResearchEnabled);
  const [status, setStatus] = useState<SecretsStatusResponse | null>(null);
  const [braveKey, setBraveKey] = useState("");
  const [exaKey, setExaKey] = useState("");
  const [vaultPassword, setVaultPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testing, setTesting] = useState<"brave_search" | "exa" | null>(null);
  const [testBrave, setTestBrave] = useState<{ valid: boolean; message: string } | null>(
    null,
  );
  const [testExa, setTestExa] = useState<{ valid: boolean; message: string } | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetchSecretsStatus();
    if (res.ok && res.data) setStatus(res.data);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const configured = status?.configured;

  const toggle = useCallback((next: boolean) => {
    setResearchEnabled(next);
    setEnabled(next);
  }, []);

  const runTest = async (provider: "brave_search" | "exa", key: string) => {
    setTesting(provider);
    const res = await testSecretKey(provider, key.trim() || undefined);
    setTesting(null);
    const payload = {
      valid: res.ok && res.data?.valid === true,
      message: res.data?.message ?? apiErrorMessage(res, "Échec du test"),
    };
    if (provider === "brave_search") setTestBrave(payload);
    else setTestExa(payload);
  };

  const saveKeys = async () => {
    if (!vaultPassword.trim()) {
      setError("Mot de passe du coffre requis pour enregistrer les clés.");
      return;
    }
    setBusy(true);
    setError(null);
    setSuccess(null);
    const res = await saveSecrets(vaultPassword, {
      brave_search_api_key: braveKey.trim() || null,
      exa_api_key: exaKey.trim() || null,
    });
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Enregistrement impossible"));
      return;
    }
    setSuccess("Clés recherche enregistrées.");
    setBraveKey("");
    setExaKey("");
    setVaultPassword("");
    await refresh();
  };

  return (
    <div className="mb-6 rounded-card border border-cf-border-input bg-cf-secondary/40 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-cf-text">Recherche de contenu activée</p>
          <p className="mt-1 text-xs text-cf-muted">
            Brave Search + Exa AI après ArchitectAI — tendances, concurrents, mots-clés
            et exemples pour un contenu réel.
          </p>
        </div>
        <ResearchToggle enabled={enabled} onChange={toggle} />
      </div>

      <div className="mt-4 space-y-3 border-t border-cf-border-input/60 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-cf-label">
          Clés API Recherche
        </p>
        <KeyField
          label="Brave Search"
          configured={Boolean(configured?.brave_search)}
          value={braveKey}
          placeholder="BSA…"
          onChange={setBraveKey}
          onTest={() => void runTest("brave_search", braveKey)}
          testing={testing === "brave_search"}
          testMessage={testBrave?.message ?? null}
          testValid={testBrave?.valid ?? null}
        />
        <KeyField
          label="Exa AI"
          configured={Boolean(configured?.exa)}
          value={exaKey}
          placeholder="exa-…"
          onChange={setExaKey}
          onTest={() => void runTest("exa", exaKey)}
          testing={testing === "exa"}
          testMessage={testExa?.message ?? null}
          testValid={testExa?.valid ?? null}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1">
            <span className="mb-1 block text-[11px] text-cf-muted">
              Mot de passe coffre (enregistrement)
            </span>
            <input
              type="password"
              value={vaultPassword}
              onChange={(e) => setVaultPassword(e.target.value)}
              className="w-full rounded-control border border-cf-border-input bg-cf-card px-3 py-2 text-xs text-cf-text"
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={() => void saveKeys()}
            className="rounded-control bg-cf-gold px-4 py-2 text-xs font-medium text-cf-main hover:bg-cf-gold-hover disabled:opacity-50"
          >
            {busy ? "Enregistrement…" : "Enregistrer les clés"}
          </button>
        </div>
        {error ? <p className="text-xs text-red-300">{error}</p> : null}
        {success ? <p className="text-xs text-cf-success">{success}</p> : null}
      </div>
    </div>
  );
}
