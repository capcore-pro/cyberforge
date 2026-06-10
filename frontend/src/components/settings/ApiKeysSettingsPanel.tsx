import { useCallback, useEffect, useMemo, useState } from "react";
import { PasswordInput } from "@/components/PasswordInput";
import {
  GLASS_CARD,
  GLASS_SECTION,
  GOLD_BTN,
  GHOST_BTN,
  openExternalUrl,
} from "@/components/settings/settings-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import { notifySecretsSaved, SECRETS_SAVED_EVENT } from "@/lib/secrets-events";
import {
  fetchSecretsStatus,
  resetSecrets,
  saveSecrets,
  testSecretKey,
  type SecretsStatusResponse,
  type VaultConfiguredFlags,
  type VaultKeysPayload,
} from "@/lib/secrets-api";

type KeyId = keyof VaultConfiguredFlags;

interface ServiceDef {
  id: KeyId;
  label: string;
  emoji: string;
  payloadKey: keyof VaultKeysPayload;
  placeholder: string;
  creditHint: string;
  topUpUrl: string;
  testable: boolean;
}

interface ServiceCategory {
  title: string;
  services: ServiceDef[];
}

const VAULT_MASK = "••••••••••••";

const CATEGORIES: ServiceCategory[] = [
  {
    title: "IA & Génération",
    services: [
      {
        id: "anthropic",
        label: "Anthropic",
        emoji: "🧠",
        payloadKey: "anthropic_api_key",
        placeholder: "sk-ant-…",
        creditHint: "~$18 restants (estim.)",
        topUpUrl: "https://console.anthropic.com",
        testable: true,
      },
      {
        id: "deepseek",
        label: "DeepSeek",
        emoji: "⚡",
        payloadKey: "deepseek_api_key",
        placeholder: "sk-…",
        creditHint: "~$5 restants (estim.)",
        topUpUrl: "https://platform.deepseek.com",
        testable: true,
      },
      {
        id: "openai",
        label: "OpenAI",
        emoji: "🤖",
        payloadKey: "openai_api_key",
        placeholder: "sk-…",
        creditHint: "Embeddings Knowledge Engine",
        topUpUrl: "https://platform.openai.com/api-keys",
        testable: true,
      },
    ],
  },
  {
    title: "Déploiement",
    services: [
      {
        id: "cloudflare",
        label: "Cloudflare",
        emoji: "☁️",
        payloadKey: "cloudflare_api_token",
        placeholder: "Token API…",
        creditHint: "Pages — gratuit",
        topUpUrl: "https://dash.cloudflare.com",
        testable: false,
      },
      {
        id: "railway",
        label: "Railway",
        emoji: "🚂",
        payloadKey: "railway_api_key",
        placeholder: "…",
        creditHint: "~$10 restants (estim.)",
        topUpUrl: "https://railway.app",
        testable: true,
      },
      {
        id: "vercel",
        label: "Vercel",
        emoji: "▲",
        payloadKey: "vercel_token",
        placeholder: "…",
        creditHint: "Hobby — gratuit",
        topUpUrl: "https://vercel.com",
        testable: true,
      },
      {
        id: "github",
        label: "GitHub",
        emoji: "🐙",
        payloadKey: "github_token",
        placeholder: "ghp_…",
        creditHint: "—",
        topUpUrl: "https://github.com/settings/tokens",
        testable: true,
      },
    ],
  },
  {
    title: "Médias & Recherche",
    services: [
      {
        id: "pexels",
        label: "Pexels",
        emoji: "📷",
        payloadKey: "pexels_api_key",
        placeholder: "…",
        creditHint: "200 req/h — gratuit",
        topUpUrl: "https://www.pexels.com/api",
        testable: false,
      },
      {
        id: "firecrawl",
        label: "Firecrawl",
        emoji: "🔥",
        payloadKey: "firecrawl_api_key",
        placeholder: "fc-…",
        creditHint: "~500 pages/mois",
        topUpUrl: "https://firecrawl.dev",
        testable: false,
      },
      {
        id: "brave_search",
        label: "Brave Search",
        emoji: "🦁",
        payloadKey: "brave_search_api_key",
        placeholder: "BSA…",
        creditHint: "~2 000 req/mois",
        topUpUrl: "https://brave.com/search/api",
        testable: true,
      },
      {
        id: "exa",
        label: "Exa AI",
        emoji: "🔍",
        payloadKey: "exa_api_key",
        placeholder: "exa-…",
        creditHint: "~1 000 req/mois",
        topUpUrl: "https://exa.ai",
        testable: true,
      },
    ],
  },
  {
    title: "Communication",
    services: [
      {
        id: "brevo",
        label: "Brevo",
        emoji: "✉️",
        payloadKey: "brevo_api_key",
        placeholder: "xkeysib-…",
        creditHint: "300 emails/jour",
        topUpUrl: "https://app.brevo.com",
        testable: true,
      },
      {
        id: "stripe",
        label: "Stripe",
        emoji: "💳",
        payloadKey: "stripe_secret_key",
        placeholder: "sk_live_…",
        creditHint: "Selon volume",
        topUpUrl: "https://dashboard.stripe.com",
        testable: true,
      },
    ],
  },
];

const EXTRA_SERVICES: ServiceDef[] = [
  {
    id: "replicate",
    label: "Replicate",
    emoji: "🎨",
    payloadKey: "replicate_api_key",
    placeholder: "r8_…",
    creditHint: "~$3 restants",
    topUpUrl: "https://replicate.com",
    testable: true,
  },
  {
    id: "tavily",
    label: "Tavily",
    emoji: "🌐",
    payloadKey: "tavily_api_key",
    placeholder: "tvly-…",
    creditHint: "1 000 crédits/mois",
    topUpUrl: "https://tavily.com",
    testable: true,
  },
  {
    id: "v0",
    label: "v0",
    emoji: "✨",
    payloadKey: "v0_api_key",
    placeholder: "v0_…",
    creditHint: "Selon abonnement",
    topUpUrl: "https://v0.dev",
    testable: true,
  },
];

const ALL_SERVICES = [
  ...CATEGORIES.flatMap((c) => c.services),
  ...EXTRA_SERVICES,
];

function ServiceKeyCard({
  def,
  configured,
  value,
  extraValue,
  onChange,
  onExtraChange,
  onTest,
  testResult,
  testing,
}: {
  def: ServiceDef;
  configured: boolean;
  value: string;
  extraValue?: string;
  onChange: (v: string) => void;
  onExtraChange?: (v: string) => void;
  onTest: () => void;
  testResult: { valid: boolean; message: string } | null;
  testing: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const isCloudflare = def.id === "cloudflare";

  return (
    <div className={GLASS_CARD}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-white">
            <span aria-hidden className="mr-1.5">
              {def.emoji}
            </span>
            {def.label}
          </p>
          <p className="mt-0.5 text-[11px] text-white/40">{def.creditHint}</p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
            configured
              ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
              : "border-red-400/35 bg-red-500/15 text-red-300"
          }`}
        >
          {configured ? "Configurée" : "Manquante"}
        </span>
      </div>

      {isCloudflare ? (
        <div className="space-y-2">
          <input
            type="text"
            autoComplete="off"
            value={extraValue ?? ""}
            onChange={(e) => onExtraChange?.(e.target.value)}
            placeholder="Account ID Cloudflare"
            className="w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 font-mono text-xs text-white focus:border-[#d4a843] focus:outline-none"
          />
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
            placeholder={
              configured ? "Laisser vide pour conserver" : "Token API Cloudflare"
            }
            className="w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 font-mono text-xs text-white focus:border-[#d4a843] focus:outline-none"
          />
        </div>
      ) : (
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
          placeholder={
            configured ? "Laisser vide pour conserver" : def.placeholder
          }
          className="w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 font-mono text-xs text-white focus:border-[#d4a843] focus:outline-none"
        />
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className={GHOST_BTN}
        >
          {visible ? "Masquer" : "Révéler"}
        </button>
        {def.testable ? (
          <button
            type="button"
            disabled={testing}
            onClick={onTest}
            className={GHOST_BTN}
          >
            {testing ? "Test…" : "Tester"}
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => openExternalUrl(def.topUpUrl)}
          className={GHOST_BTN}
        >
          Recréditer →
        </button>
      </div>

      {testResult ? (
        <p
          className={`mt-2 text-xs ${
            testResult.valid ? "text-emerald-300" : "text-red-300"
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
  const [showMore, setShowMore] = useState(false);
  const [vaultPassword, setVaultPassword] = useState("");

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
    brave_search_api_key: "",
    exa_api_key: "",
    pexels_api_key: "",
    firecrawl_api_key: "",
    cloudflare_account_id: "",
    cloudflare_api_token: "",
  });

  const [testResults, setTestResults] = useState<
    Partial<Record<KeyId, { valid: boolean; message: string }>>
  >({});
  const [testingId, setTestingId] = useState<KeyId | null>(null);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    const res = await fetchSecretsStatus();
    if (res.ok && res.data) setStatus(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    const onSecretsSaved = () => void refreshStatus();
    window.addEventListener(SECRETS_SAVED_EVENT, onSecretsSaved);
    return () => window.removeEventListener(SECRETS_SAVED_EVENT, onSecretsSaved);
  }, [refreshStatus]);

  const configured = status?.configured ?? ({} as VaultConfiguredFlags);

  const { configuredCount, missingCount, progressPct } = useMemo(() => {
    const total = ALL_SERVICES.length;
    const done = ALL_SERVICES.filter((s) => configured[s.id]).length;
    return {
      configuredCount: done,
      missingCount: total - done,
      progressPct: total ? Math.round((done / total) * 100) : 0,
    };
  }, [configured]);

  async function handleTest(def: ServiceDef) {
    setTestingId(def.id);
    const res = await testSecretKey(
      def.id,
      values[def.payloadKey]?.trim() || undefined,
    );
    setTestingId(null);
    if (!res.ok || !res.data) {
      setTestResults((prev) => ({
        ...prev,
        [def.id]: {
          valid: false,
          message: apiErrorMessage(res, "Test impossible."),
        },
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
    for (const def of ALL_SERVICES) {
      const trimmed = values[def.payloadKey]?.trim();
      if (trimmed) keys[def.payloadKey] = trimmed;
    }
    const cfAccount = values.cloudflare_account_id?.trim();
    const cfToken = values.cloudflare_api_token?.trim();
    if (cfAccount) keys.cloudflare_account_id = cfAccount;
    if (cfToken) keys.cloudflare_api_token = cfToken;

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
      for (const def of ALL_SERVICES) cleared[def.payloadKey] = "";
      cleared.cloudflare_account_id = "";
      cleared.cloudflare_api_token = "";
      return cleared;
    });
    notifySecretsSaved();
    await refreshStatus();
  }

  async function handleResetVault() {
    const vaultPath =
      status?.vault_path ?? "%LOCALAPPDATA%\\CyberForge\\secrets.v1.json";
    const ok = window.confirm(
      `Réinitialiser le coffre des clés API ?\n\nFichier : ${vaultPath}`,
    );
    if (!ok) return;
    setBusy(true);
    const res = await resetSecrets();
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Réinitialisation impossible."));
      return;
    }
    if (res.data) setStatus(res.data);
    setVaultPassword("");
    setTestResults({});
    setSuccess("Coffre réinitialisé.");
    notifySecretsSaved();
    await refreshStatus();
  }

  if (loading) {
    return (
      <p className="animate-pulse text-sm text-white/50">Chargement des clés…</p>
    );
  }

  return (
    <div className="space-y-6">
      <div className={GLASS_SECTION}>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Crédits globaux</p>
            <p className="mt-1 text-xs text-white/50">
              {configuredCount} clés configurées · {missingCount} manquantes
            </p>
          </div>
          <span className="text-2xl font-bold text-[#d4a843]">{progressPct}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#d4a843]/60 to-[#d4a843] transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {CATEGORIES.map((category) => (
        <div key={category.title}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
            {category.title}
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {category.services.map((def) => (
              <ServiceKeyCard
                key={def.id}
                def={def}
                configured={Boolean(configured[def.id])}
                value={values[def.payloadKey]}
                extraValue={
                  def.id === "cloudflare"
                    ? values.cloudflare_account_id
                    : undefined
                }
                onChange={(v) =>
                  setValues((prev) => ({ ...prev, [def.payloadKey]: v }))
                }
                onExtraChange={
                  def.id === "cloudflare"
                    ? (v) =>
                        setValues((prev) => ({
                          ...prev,
                          cloudflare_account_id: v,
                        }))
                    : undefined
                }
                onTest={() => void handleTest(def)}
                testResult={testResults[def.id] ?? null}
                testing={testingId === def.id}
              />
            ))}
          </div>
        </div>
      ))}

      <div>
        <button
          type="button"
          onClick={() => setShowMore((v) => !v)}
          className="mb-3 text-sm text-[#d4a843] hover:underline"
        >
          {showMore ? "Masquer les services avancés" : "Afficher plus"}
        </button>
        {showMore ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {EXTRA_SERVICES.map((def) => (
              <ServiceKeyCard
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
            <div className={`${GLASS_CARD} opacity-80`}>
              <p className="text-sm font-semibold text-white">
                <span className="mr-1.5">🤖</span>
                OpenHands
              </p>
              <p className="mt-1 text-xs text-white/45">
                Module optionnel — configuration via environnement.
              </p>
              <span className="mt-2 inline-block rounded-full border border-white/20 px-2 py-0.5 text-[10px] text-white/50">
                Module intégré
              </span>
            </div>
            <div className={`${GLASS_CARD} opacity-80`}>
              <p className="text-sm font-semibold text-white">
                <span className="mr-1.5">🎭</span>
                Playwright
              </p>
              <p className="mt-1 text-xs text-white/45">
                Tests E2E locaux — pas de clé API requise.
              </p>
              <span className="mt-2 inline-block rounded-full border border-emerald-400/35 bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
                Inclus
              </span>
            </div>
            <div className={`${GLASS_CARD} opacity-80`}>
              <p className="text-sm font-semibold text-white">
                <span className="mr-1.5">🏮</span>
                Lighthouse
              </p>
              <p className="mt-1 text-xs text-white/45">
                Audit qualité local — pas de clé API requise.
              </p>
              <span className="mt-2 inline-block rounded-full border border-emerald-400/35 bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
                Inclus
              </span>
            </div>
          </div>
        ) : null}
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
          Coffre-fort
        </h3>
        <label className="block">
          <span className="mb-2 block text-sm text-white/60">
            Mot de passe du coffre
          </span>
          <PasswordInput
            autoComplete="current-password"
            value={vaultPassword}
            onChange={(e) => setVaultPassword(e.target.value)}
            placeholder="Chiffre toutes les clés sur cet appareil"
            containerClassName="max-w-md"
          />
        </label>
        {status ? (
          <p className="mt-2 text-[11px] text-white/40">
            Coffre {status.has_vault ? "actif" : "non créé"} —{" "}
            {status.locked ? "verrouillé" : "déverrouillé"}
          </p>
        ) : null}
        <button
          type="button"
          disabled={busy || !status?.has_vault}
          onClick={() => void handleResetVault()}
          className="mt-4 text-xs text-red-300 hover:underline disabled:opacity-40"
        >
          Réinitialiser le coffre
        </button>
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
        disabled={busy}
        onClick={() => void handleSaveAll()}
        className={`${GOLD_BTN} w-full sm:w-auto`}
      >
        {busy ? "Enregistrement…" : "Enregistrer toutes les clés"}
      </button>
    </div>
  );
}
