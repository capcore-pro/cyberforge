import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  cancelStripeSubscription,
  createStripeConfig,
  createSubscriptionLink,
  deleteStripeConfig,
  fetchStripeConfigs,
  fetchStripeDashboard,
  fetchStripeSubscriptions,
  fetchStripeTransactions,
  updateStripeConfig,
  type StripeConfig,
  type StripeConfigCreatePayload,
  type StripeDashboard,
  type StripeMode,
  type StripeSubscription,
  type StripeTransaction,
} from "@/lib/stripe-api";

type StripeSection = "dashboard" | "configs" | "subscriptions";

const SECTIONS: { id: StripeSection; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "configs", label: "Configurations" },
  { id: "subscriptions", label: "Abonnements" },
];

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

function formatEur(value: number): string {
  return eurFmt.format(value);
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function monthKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key: string): string {
  const [y, m] = key.split("-");
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
}

function revenueByMonth(
  transactions: StripeTransaction[],
  monthCount = 3,
): { key: string; label: string; total: number }[] {
  const now = new Date();
  const keys: string[] = [];
  for (let i = monthCount - 1; i >= 0; i -= 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    keys.push(monthKey(d));
  }
  const totals = new Map(keys.map((k) => [k, 0]));
  for (const tx of transactions) {
    if (tx.status !== "paid") continue;
    const created = new Date(tx.created_at);
    const k = monthKey(created);
    if (totals.has(k)) {
      totals.set(k, (totals.get(k) ?? 0) + Number(tx.amount_eur || 0));
    }
  }
  return keys.map((key) => ({
    key,
    label: monthLabel(key),
    total: totals.get(key) ?? 0,
  }));
}

function SubTabs({
  current,
  onChange,
}: {
  current: StripeSection;
  onChange: (s: StripeSection) => void;
}) {
  return (
    <div className="mb-6 flex flex-wrap gap-2 border-b border-cyber-border pb-3">
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onChange(s.id)}
          className={`rounded-md px-4 py-2 text-xs font-bold uppercase tracking-wider transition ${
            current === s.id
              ? "border border-cyber-neon bg-cyber-accent/10 text-cyber-neon shadow-neonCyan"
              : "border border-transparent text-cyber-muted hover:border-cyber-border hover:text-cyber-text"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 rounded-lg border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
      {message}
    </div>
  );
}

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "green" | "amber" | "red" | "muted" | "blue";
}) {
  const tones = {
    green: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
    amber: "border-amber-500/40 bg-amber-500/15 text-amber-200",
    red: "border-red-500/40 bg-red-500/15 text-red-300",
    muted: "border-cyber-border bg-cyber-panel/50 text-cyber-muted",
    blue: "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
  };
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${tones[tone]}`}
    >
      {label}
    </span>
  );
}

function txStatusTone(status: string): "green" | "amber" | "red" | "muted" {
  if (status === "paid") return "green";
  if (status === "pending") return "amber";
  if (status === "failed") return "red";
  return "muted";
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "green" | "blue" | "violet" | "cyan";
}) {
  const accents = {
    green:
      "border-emerald-500/30 bg-gradient-to-br from-emerald-950/60 to-cyber-panel shadow-[0_0_24px_rgba(16,185,129,0.12)]",
    blue: "border-cyan-500/30 bg-gradient-to-br from-cyan-950/50 to-cyber-panel shadow-[0_0_24px_rgba(6,182,212,0.12)]",
    violet:
      "border-violet-500/30 bg-gradient-to-br from-violet-950/40 to-cyber-panel shadow-[0_0_20px_rgba(139,92,246,0.1)]",
    cyan: "border-cyber-neon/25 bg-gradient-to-br from-cyber-accent/10 to-cyber-panel",
  };
  const valueColors = {
    green: "text-emerald-400",
    blue: "text-cyan-400",
    violet: "text-violet-300",
    cyan: "text-cyber-neon",
  };
  return (
    <div className={`rounded-lg border p-4 ${accents[accent]}`}>
      <p className="text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-bold tabular-nums ${valueColors[accent]}`}>
        {value}
      </p>
    </div>
  );
}

function RevenueChart({ months }: { months: { label: string; total: number }[] }) {
  const max = Math.max(...months.map((m) => m.total), 1);
  return (
    <div className="rounded-lg border border-cyber-border bg-cyber-panel/40 p-4">
      <h3 className="mb-4 text-xs font-bold uppercase tracking-wider text-cyber-muted">
        Revenus par mois (3 derniers mois)
      </h3>
      <div className="flex items-end justify-around gap-4" style={{ minHeight: 140 }}>
        {months.map((m) => {
          const pct = Math.round((m.total / max) * 100);
          return (
            <div key={m.label} className="flex flex-1 flex-col items-center gap-2">
              <span className="text-[10px] text-cyber-muted tabular-nums">
                {formatEur(m.total)}
              </span>
              <div
                className="w-full max-w-[72px] rounded-t bg-gradient-to-t from-emerald-600/80 to-emerald-400/90 transition-all"
                style={{ height: `${Math.max(8, pct)}%`, minHeight: 8 }}
                title={formatEur(m.total)}
              />
              <span className="text-center text-[10px] font-medium capitalize text-cyber-text">
                {m.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="stripe-modal-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-cyber-border bg-cyber-panel shadow-xl">
        <div className="flex items-center justify-between border-b border-cyber-border px-4 py-3">
          <h2 id="stripe-modal-title" className="text-sm font-bold text-cyber-text">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded px-2 py-1 text-cyber-muted hover:bg-cyber-border/50 hover:text-cyber-text"
            aria-label="Fermer"
          >
            ✕
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

function ConfigFormFields({
  values,
  onChange,
  secretOptional,
}: {
  values: {
    project_id: string;
    project_name: string;
    publishable_key: string;
    secret_key: string;
    webhook_secret: string;
    mode: StripeMode;
    currency: string;
  };
  onChange: (patch: Partial<typeof values>) => void;
  secretOptional?: boolean;
}) {
  const inputClass =
    "mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text focus:border-cyber-neon focus:outline-none";
  const labelClass = "block text-[10px] font-bold uppercase tracking-wider text-cyber-muted";

  return (
    <div className="space-y-3">
      <label className="block">
        <span className={labelClass}>ID projet</span>
        <input
          className={inputClass}
          value={values.project_id}
          onChange={(e) => onChange({ project_id: e.target.value })}
          placeholder="uuid ou capcore"
        />
      </label>
      <label className="block">
        <span className={labelClass}>Nom projet</span>
        <input
          className={inputClass}
          value={values.project_name}
          onChange={(e) => onChange({ project_name: e.target.value })}
        />
      </label>
      <label className="block">
        <span className={labelClass}>Clé publique</span>
        <input
          className={inputClass}
          value={values.publishable_key}
          onChange={(e) => onChange({ publishable_key: e.target.value })}
          placeholder="pk_test_…"
        />
      </label>
      <label className="block">
        <span className={labelClass}>
          Clé secrète{secretOptional ? " (laisser vide pour ne pas modifier)" : ""}
        </span>
        <input
          type="password"
          className={inputClass}
          value={values.secret_key}
          onChange={(e) => onChange({ secret_key: e.target.value })}
          placeholder="sk_test_…"
          autoComplete="off"
        />
      </label>
      <label className="block">
        <span className={labelClass}>Webhook secret (optionnel)</span>
        <input
          type="password"
          className={inputClass}
          value={values.webhook_secret}
          onChange={(e) => onChange({ webhook_secret: e.target.value })}
          placeholder="whsec_…"
          autoComplete="off"
        />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className={labelClass}>Mode</span>
          <select
            className={inputClass}
            value={values.mode}
            onChange={(e) => onChange({ mode: e.target.value as StripeMode })}
          >
            <option value="test">Test</option>
            <option value="live">Live</option>
          </select>
        </label>
        <label className="block">
          <span className={labelClass}>Devise</span>
          <input
            className={inputClass}
            value={values.currency}
            onChange={(e) => onChange({ currency: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}

// --- Dashboard ---

function DashboardSection({
  dashboard,
  transactions,
  projectNames,
}: {
  dashboard: StripeDashboard;
  transactions: StripeTransaction[];
  projectNames: Map<string, string>;
}) {
  const months = useMemo(
    () => revenueByMonth(transactions, 3),
    [transactions],
  );
  const rows =
    transactions.length > 0
      ? transactions.slice(0, 25)
      : dashboard.recent_transactions;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="CA total"
          value={formatEur(dashboard.total_collected_eur)}
          accent="green"
        />
        <MetricCard
          label="CA ce mois"
          value={formatEur(dashboard.revenue_this_month_eur)}
          accent="green"
        />
        <MetricCard
          label="MRR"
          value={formatEur(dashboard.active_subscriptions_mrr_eur)}
          accent="blue"
        />
        <MetricCard
          label="Abonnements actifs"
          value={String(dashboard.active_subscriptions_count)}
          accent="violet"
        />
      </div>

      <RevenueChart months={months} />

      <div className="overflow-hidden rounded-lg border border-cyber-border">
        <div className="border-b border-cyber-border bg-cyber-panel/60 px-4 py-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-cyber-muted">
            Dernières transactions
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead>
              <tr className="border-b border-cyber-border text-[10px] uppercase tracking-wider text-cyber-muted">
                <th className="px-3 py-2 font-bold">Projet</th>
                <th className="px-3 py-2 font-bold">Client</th>
                <th className="px-3 py-2 font-bold text-right">Montant</th>
                <th className="px-3 py-2 font-bold">Type</th>
                <th className="px-3 py-2 font-bold">Statut</th>
                <th className="px-3 py-2 font-bold">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-cyber-muted">
                    Aucune transaction enregistrée.
                  </td>
                </tr>
              ) : (
                rows.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                  >
                    <td className="px-3 py-2 text-cyber-text">
                      {projectNames.get(tx.project_id) ?? tx.project_id}
                    </td>
                    <td className="max-w-[140px] truncate px-3 py-2 text-cyber-muted">
                      {tx.customer_email || "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-medium tabular-nums text-emerald-400">
                      {formatEur(Number(tx.amount_eur))}
                    </td>
                    <td className="px-3 py-2">
                      <StatusPill
                        label={tx.type === "subscription" ? "Abo" : "One-shot"}
                        tone="blue"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <StatusPill label={tx.status} tone={txStatusTone(tx.status)} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-cyber-muted">
                      {formatDate(tx.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// --- Configurations ---

function ConfigsSection({
  configs,
  loading,
  onRefresh,
}: {
  configs: StripeConfig[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [editConfig, setEditConfig] = useState<StripeConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    project_id: "",
    project_name: "",
    publishable_key: "",
    secret_key: "",
    webhook_secret: "",
    mode: "test" as StripeMode,
    currency: "eur",
  });

  const resetForm = () => {
    setForm({
      project_id: "",
      project_name: "",
      publishable_key: "",
      secret_key: "",
      webhook_secret: "",
      mode: "test",
      currency: "eur",
    });
  };

  const openEdit = (cfg: StripeConfig) => {
    setEditConfig(cfg);
    setForm({
      project_id: cfg.project_id,
      project_name: cfg.project_name,
      publishable_key: cfg.publishable_key,
      secret_key: "",
      webhook_secret: "",
      mode: cfg.mode,
      currency: cfg.currency,
    });
    setError(null);
  };

  const handleCreate = async () => {
    setBusy(true);
    setError(null);
    const body: StripeConfigCreatePayload = {
      project_id: form.project_id.trim(),
      project_name: form.project_name.trim(),
      publishable_key: form.publishable_key.trim(),
      secret_key: form.secret_key.trim(),
      webhook_secret: form.webhook_secret.trim() || null,
      mode: form.mode,
      currency: form.currency.trim() || "eur",
    };
    const res = await createStripeConfig(body);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Backend injoignable"));
      return;
    }
    setShowAdd(false);
    resetForm();
    onRefresh();
  };

  const handleUpdate = async () => {
    if (!editConfig) return;
    setBusy(true);
    setError(null);
    const patch: Record<string, unknown> = {
      project_id: form.project_id.trim(),
      project_name: form.project_name.trim(),
      publishable_key: form.publishable_key.trim(),
      mode: form.mode,
      currency: form.currency.trim() || "eur",
    };
    if (form.secret_key.trim()) patch.secret_key = form.secret_key.trim();
    if (form.webhook_secret.trim()) patch.webhook_secret = form.webhook_secret.trim();

    const res = await updateStripeConfig(editConfig.id, patch);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Backend injoignable"));
      return;
    }
    setEditConfig(null);
    resetForm();
    onRefresh();
  };

  const handleDelete = async (cfg: StripeConfig) => {
    const ok = window.confirm(
      `Supprimer la configuration Stripe pour « ${cfg.project_name} » ?`,
    );
    if (!ok) return;
    const res = await deleteStripeConfig(cfg.id);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Backend injoignable"));
      return;
    }
    onRefresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-cyber-muted">
          {configs.length} configuration{configs.length !== 1 ? "s" : ""} Stripe
        </p>
        <button
          type="button"
          onClick={() => {
            resetForm();
            setError(null);
            setShowAdd(true);
          }}
          className="rounded border border-cyber-neon bg-cyber-accent/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-cyber-neon hover:bg-cyber-accent/20"
        >
          Ajouter
        </button>
      </div>

      {error ? <ErrorBanner message={error} /> : null}

      <div className="overflow-hidden rounded-lg border border-cyber-border">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-cyber-border bg-cyber-panel/60 text-[10px] uppercase tracking-wider text-cyber-muted">
              <th className="px-3 py-2 font-bold">Projet</th>
              <th className="px-3 py-2 font-bold">Mode</th>
              <th className="px-3 py-2 font-bold">Devise</th>
              <th className="px-3 py-2 font-bold">Statut</th>
              <th className="px-3 py-2 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-cyber-muted">
                  Chargement…
                </td>
              </tr>
            ) : configs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-cyber-muted">
                  Aucune configuration — ajoutez un projet Stripe.
                </td>
              </tr>
            ) : (
              configs.map((cfg) => (
                <tr
                  key={cfg.id}
                  className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                >
                  <td className="px-3 py-2">
                    <p className="font-medium text-cyber-text">{cfg.project_name}</p>
                    <p className="text-[10px] text-cyber-muted">{cfg.project_id}</p>
                  </td>
                  <td className="px-3 py-2">
                    <StatusPill
                      label={cfg.mode}
                      tone={cfg.mode === "live" ? "green" : "amber"}
                    />
                  </td>
                  <td className="px-3 py-2 uppercase text-cyber-muted">{cfg.currency}</td>
                  <td className="px-3 py-2">
                    <StatusPill
                      label={cfg.enabled ? "Actif" : "Désactivé"}
                      tone={cfg.enabled ? "green" : "muted"}
                    />
                  </td>
                  <td className="space-x-2 px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => openEdit(cfg)}
                      className="rounded border border-cyber-border px-2 py-1 text-[10px] font-bold uppercase text-cyber-text hover:border-cyber-neon"
                    >
                      Configurer
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(cfg)}
                      className="rounded border border-red-500/40 px-2 py-1 text-[10px] font-bold uppercase text-red-300 hover:bg-red-950/40"
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAdd ? (
        <ModalShell title="Ajouter une configuration Stripe" onClose={() => setShowAdd(false)}>
          <ConfigFormFields values={form} onChange={(p) => setForm((f) => ({ ...f, ...p }))} />
          {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded border border-cyber-border px-3 py-2 text-xs text-cyber-muted"
            >
              Annuler
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleCreate()}
              className="rounded border border-cyber-neon bg-cyber-accent/10 px-4 py-2 text-xs font-bold uppercase text-cyber-neon disabled:opacity-50"
            >
              {busy ? "Enregistrement…" : "Enregistrer"}
            </button>
          </div>
        </ModalShell>
      ) : null}

      {editConfig ? (
        <ModalShell
          title={`Configurer — ${editConfig.project_name}`}
          onClose={() => setEditConfig(null)}
        >
          <ConfigFormFields
            values={form}
            onChange={(p) => setForm((f) => ({ ...f, ...p }))}
            secretOptional
          />
          {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditConfig(null)}
              className="rounded border border-cyber-border px-3 py-2 text-xs text-cyber-muted"
            >
              Annuler
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleUpdate()}
              className="rounded border border-cyber-neon bg-cyber-accent/10 px-4 py-2 text-xs font-bold uppercase text-cyber-neon disabled:opacity-50"
            >
              {busy ? "Mise à jour…" : "Enregistrer"}
            </button>
          </div>
        </ModalShell>
      ) : null}
    </div>
  );
}

// --- Abonnements ---

function SubscriptionsSection({
  subscriptions,
  configs,
  loading,
  onRefresh,
}: {
  subscriptions: StripeSubscription[];
  configs: StripeConfig[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const [showLink, setShowLink] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkResult, setLinkResult] = useState<string | null>(null);
  const [linkForm, setLinkForm] = useState({
    project_id: "",
    plan_name: "",
    amount_eur: "",
    customer_email: "",
  });

  const projectNames = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of configs) m.set(c.project_id, c.project_name);
    return m;
  }, [configs]);

  const openLinkModal = () => {
    setLinkForm({
      project_id: configs[0]?.project_id ?? "capcore",
      plan_name: "",
      amount_eur: "",
      customer_email: "",
    });
    setLinkResult(null);
    setError(null);
    setShowLink(true);
  };

  const handleGenerateLink = async () => {
    const amount = parseFloat(linkForm.amount_eur.replace(",", "."));
    if (!linkForm.project_id.trim() || !linkForm.plan_name.trim() || !(amount > 0)) {
      setError("Projet, plan et montant (> 0) requis.");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await createSubscriptionLink({
      project_id: linkForm.project_id.trim(),
      plan_name: linkForm.plan_name.trim(),
      amount_eur: amount,
      customer_email: linkForm.customer_email.trim() || null,
      interval: "month",
    });
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Backend injoignable"));
      return;
    }
    const url = (res.data as { url?: string })?.url ?? "";
    setLinkResult(url);
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* copie manuelle */
    }
  };

  const handleCancel = async (sub: StripeSubscription) => {
    const ok = window.confirm(
      `Annuler l'abonnement « ${sub.plan_name} » pour ${sub.customer_email} ?`,
    );
    if (!ok) return;
    const res = await cancelStripeSubscription(sub.id);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Backend injoignable"));
      return;
    }
    onRefresh();
  };

  const inputClass =
    "mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text focus:border-cyber-neon focus:outline-none";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-cyber-muted">
          {subscriptions.length} abonnement{subscriptions.length !== 1 ? "s" : ""} actif
          {subscriptions.length !== 1 ? "s" : ""}
        </p>
        <button
          type="button"
          onClick={openLinkModal}
          className="rounded border border-cyan-500/50 bg-cyan-500/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-cyan-300 hover:bg-cyan-500/20"
        >
          Générer lien abonnement
        </button>
      </div>

      {error && !showLink ? <ErrorBanner message={error} /> : null}

      <div className="overflow-hidden rounded-lg border border-cyber-border">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-cyber-border bg-cyber-panel/60 text-[10px] uppercase tracking-wider text-cyber-muted">
              <th className="px-3 py-2 font-bold">Client</th>
              <th className="px-3 py-2 font-bold">Projet</th>
              <th className="px-3 py-2 font-bold">Plan</th>
              <th className="px-3 py-2 font-bold text-right">€/mois</th>
              <th className="px-3 py-2 font-bold">Prochain prélèvement</th>
              <th className="px-3 py-2 font-bold">Statut</th>
              <th className="px-3 py-2 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-cyber-muted">
                  Chargement…
                </td>
              </tr>
            ) : subscriptions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-cyber-muted">
                  Aucun abonnement actif.
                </td>
              </tr>
            ) : (
              subscriptions.map((sub) => (
                <tr
                  key={sub.id}
                  className="border-b border-cyber-border/60 hover:bg-cyber-accent/5"
                >
                  <td className="max-w-[160px] truncate px-3 py-2 text-cyber-text">
                    {sub.customer_email}
                  </td>
                  <td className="px-3 py-2 text-cyber-muted">
                    {projectNames.get(sub.project_id) ?? sub.project_id}
                  </td>
                  <td className="px-3 py-2 text-cyber-text">{sub.plan_name}</td>
                  <td className="px-3 py-2 text-right font-medium tabular-nums text-cyan-400">
                    {formatEur(Number(sub.amount_eur))}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-cyber-muted">
                    {formatDate(sub.current_period_end)}
                  </td>
                  <td className="px-3 py-2">
                    <StatusPill
                      label={sub.status}
                      tone={sub.status === "active" ? "green" : "amber"}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => void handleCancel(sub)}
                      className="rounded border border-red-500/40 px-2 py-1 text-[10px] font-bold uppercase text-red-300 hover:bg-red-950/40"
                    >
                      Annuler
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showLink ? (
        <ModalShell title="Lien d'abonnement Stripe" onClose={() => setShowLink(false)}>
          <div className="space-y-3">
            <label className="block text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
              Projet
              <select
                className={inputClass}
                value={linkForm.project_id}
                onChange={(e) =>
                  setLinkForm((f) => ({ ...f, project_id: e.target.value }))
                }
              >
                {configs.length === 0 ? (
                  <option value="capcore">capcore (défaut)</option>
                ) : (
                  configs.map((c) => (
                    <option key={c.id} value={c.project_id}>
                      {c.project_name}
                    </option>
                  ))
                )}
              </select>
            </label>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
              Plan
              <input
                className={inputClass}
                value={linkForm.plan_name}
                onChange={(e) =>
                  setLinkForm((f) => ({ ...f, plan_name: e.target.value }))
                }
                placeholder="Pro Mensuel"
              />
            </label>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
              Montant (EUR / mois)
              <input
                className={inputClass}
                type="number"
                min={0}
                step={0.01}
                value={linkForm.amount_eur}
                onChange={(e) =>
                  setLinkForm((f) => ({ ...f, amount_eur: e.target.value }))
                }
              />
            </label>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-cyber-muted">
              Email client (optionnel)
              <input
                className={inputClass}
                type="email"
                value={linkForm.customer_email}
                onChange={(e) =>
                  setLinkForm((f) => ({ ...f, customer_email: e.target.value }))
                }
              />
            </label>
          </div>
          {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
          {linkResult ? (
            <div className="mt-3 rounded border border-emerald-500/30 bg-emerald-950/30 p-3">
              <p className="text-[10px] font-bold uppercase text-emerald-400">
                Lien copié dans le presse-papiers
              </p>
              <p className="mt-1 break-all text-xs text-cyber-text">{linkResult}</p>
            </div>
          ) : null}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowLink(false)}
              className="rounded border border-cyber-border px-3 py-2 text-xs text-cyber-muted"
            >
              Fermer
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleGenerateLink()}
              className="rounded border border-cyan-500/50 bg-cyan-500/10 px-4 py-2 text-xs font-bold uppercase text-cyan-300 disabled:opacity-50"
            >
              {busy ? "Génération…" : "Générer et copier"}
            </button>
          </div>
        </ModalShell>
      ) : null}
    </div>
  );
}

/**
 * Module Stripe — dashboard, configurations et abonnements.
 */
export function StripePage() {
  const [section, setSection] = useState<StripeSection>("dashboard");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [dashboard, setDashboard] = useState<StripeDashboard | null>(null);
  const [transactions, setTransactions] = useState<StripeTransaction[]>([]);
  const [configs, setConfigs] = useState<StripeConfig[]>([]);
  const [subscriptions, setSubscriptions] = useState<StripeSubscription[]>([]);

  const projectNames = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of configs) m.set(c.project_id, c.project_name);
    return m;
  }, [configs]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    const offline = "Backend injoignable — vérifiez que l'API tourne sur le port 8002.";

    const [dashRes, txRes, cfgRes, subRes] = await Promise.all([
      fetchStripeDashboard(),
      fetchStripeTransactions({ status: "paid", limit: 500 }),
      fetchStripeConfigs(),
      fetchStripeSubscriptions({ status: "active", limit: 200 }),
    ]);

    setLoading(false);

    if (!dashRes.ok) {
      setError(apiErrorMessage(dashRes, offline));
      return;
    }
    setDashboard(dashRes.data);
    if (txRes.ok && Array.isArray(txRes.data)) setTransactions(txRes.data);
    if (cfgRes.ok && Array.isArray(cfgRes.data)) setConfigs(cfgRes.data);
    if (subRes.ok && Array.isArray(subRes.data)) setSubscriptions(subRes.data);

    if (!cfgRes.ok) {
      setError(apiErrorMessage(cfgRes, offline));
    }
  }, []);

  const refreshConfigs = useCallback(async () => {
    const res = await fetchStripeConfigs();
    if (res.ok && Array.isArray(res.data)) setConfigs(res.data);
  }, []);

  const refreshSubscriptions = useCallback(async () => {
    const res = await fetchStripeSubscriptions({ status: "active", limit: 200 });
    if (res.ok && Array.isArray(res.data)) setSubscriptions(res.data);
    const dashRes = await fetchStripeDashboard();
    if (dashRes.ok) setDashboard(dashRes.data);
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-cyber-text">
            Stripe CapCore
          </h1>
          <p className="mt-1 text-sm text-cyber-muted">
            Paiements, abonnements et configurations par projet — clé CapCore par défaut.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadAll()}
          disabled={loading}
          className="rounded border border-cyber-border px-3 py-2 text-xs font-bold uppercase tracking-wider text-cyber-muted hover:border-cyber-neon hover:text-cyber-neon disabled:opacity-50"
        >
          Actualiser
        </button>
      </header>

      {error ? <ErrorBanner message={error} /> : null}

      <SubTabs current={section} onChange={setSection} />

      {loading && !dashboard ? (
        <p className="text-sm text-cyber-muted animate-pulse">Chargement Stripe…</p>
      ) : null}

      {section === "dashboard" && dashboard ? (
        <DashboardSection
          dashboard={dashboard}
          transactions={transactions}
          projectNames={projectNames}
        />
      ) : null}

      {section === "configs" ? (
        <ConfigsSection
          configs={configs}
          loading={loading}
          onRefresh={() => void refreshConfigs()}
        />
      ) : null}

      {section === "subscriptions" ? (
        <SubscriptionsSection
          subscriptions={subscriptions}
          configs={configs}
          loading={loading}
          onRefresh={() => void refreshSubscriptions()}
        />
      ) : null}
    </div>
  );
}
