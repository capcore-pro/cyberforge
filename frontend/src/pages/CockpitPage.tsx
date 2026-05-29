import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  COCKPIT_CONNECTOR_OPTIONS,
  createCockpitService,
  deleteCockpitService,
  fetchCockpitDashboard,
  fetchCockpitServices,
  fetchCockpitTransactions,
  markCockpitAlertsRead,
  syncAllCockpitServices,
  topupCockpitService,
  updateCockpitService,
  updateCockpitThresholds,
  type AlertLevel,
  type CockpitAlert,
  type CockpitDashboard,
  type CockpitService,
  type CockpitThresholds,
  type CockpitTransaction,
  type TransactionType,
} from "@/lib/cockpit-api";

type CockpitSection = "dashboard" | "wallet" | "thresholds" | "settings";

const SECTIONS: { id: CockpitSection; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "wallet", label: "Wallet" },
  { id: "thresholds", label: "Seuils" },
  { id: "settings", label: "Paramètres" },
];

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

function formatEur(value: number): string {
  return eurFmt.format(value);
}

function balanceOf(service: CockpitService): number {
  return Number(service.balance?.balance_eur ?? 0);
}

function thresholdAlertLevel(
  balance: number,
  thresholds: CockpitThresholds,
): AlertLevel | null {
  if (balance <= thresholds.urgent_eur) return "urgent";
  if (balance <= thresholds.critical_eur) return "critical";
  if (balance <= thresholds.warning_eur) return "warning";
  return null;
}

function alertBadgeClass(level: AlertLevel): string {
  if (level === "urgent") return "bg-red-500/20 text-red-300 border-red-500/50";
  if (level === "critical") return "bg-orange-500/20 text-orange-200 border-orange-500/50";
  return "bg-amber-500/20 text-amber-200 border-amber-500/50";
}

function alertBannerClass(level: AlertLevel): string {
  if (level === "urgent") return "border-red-500/60 bg-red-950/50 text-red-100";
  if (level === "critical") return "border-orange-500/60 bg-orange-950/40 text-orange-100";
  return "border-amber-500/50 bg-amber-950/30 text-amber-100";
}

function worstAlertLevel(alerts: CockpitAlert[]): AlertLevel | null {
  if (alerts.some((a) => a.level === "urgent")) return "urgent";
  if (alerts.some((a) => a.level === "critical")) return "critical";
  if (alerts.some((a) => a.level === "warning")) return "warning";
  return null;
}

function serviceBorderStyle(color: string | null): CSSProperties {
  const c = color?.trim() || "#06b6d4";
  return {
    borderColor: c,
    boxShadow: `0 0 20px ${c}22, inset 0 1px 0 ${c}33`,
  };
}

function SubTabs({
  current,
  onChange,
}: {
  current: CockpitSection;
  onChange: (s: CockpitSection) => void;
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

function LoadingBlock() {
  return (
    <p className="text-sm text-cyber-muted animate-pulse">Chargement du cockpit…</p>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 rounded-lg border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
      {message}
    </div>
  );
}

// --- Dashboard ---

function DashboardSection({
  dashboard,
  syncing,
  onSyncAll,
  onDismissAlerts,
  dismissingAlerts,
}: {
  dashboard: CockpitDashboard;
  syncing: boolean;
  onSyncAll: () => void;
  onDismissAlerts: () => void;
  dismissingAlerts: boolean;
}) {
  const bannerLevel = worstAlertLevel(dashboard.unread_alerts);

  return (
    <div className="space-y-6">
      {dashboard.unread_alerts.length > 0 && bannerLevel ? (
        <div
          className={`rounded-lg border px-4 py-3 ${alertBannerClass(bannerLevel)}`}
          role="alert"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider">
                {dashboard.unread_alerts_count} alerte
                {dashboard.unread_alerts_count > 1 ? "s" : ""} non lue
              </p>
              <ul className="mt-2 space-y-1 text-sm">
                {dashboard.unread_alerts.slice(0, 5).map((a) => (
                  <li key={a.id}>{a.message}</li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              className="cyber-action-btn shrink-0"
              disabled={dismissingAlerts}
              onClick={onDismissAlerts}
            >
              Marquer comme lues
            </button>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid flex-1 gap-3 sm:grid-cols-3">
          <div className="cyber-metric-tile cyber-metric-tile-highlight">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Aujourd&apos;hui
            </p>
            <p className="mt-1 text-2xl font-bold text-cyber-neon">
              {formatEur(dashboard.spent_today_eur)}
            </p>
          </div>
          <div className="cyber-metric-tile">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Cette semaine
            </p>
            <p className="mt-1 text-2xl font-bold text-cyber-text">
              {formatEur(dashboard.spent_week_eur)}
            </p>
          </div>
          <div className="cyber-metric-tile">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Ce mois
            </p>
            <p className="mt-1 text-2xl font-bold text-cyber-violet">
              {formatEur(dashboard.month_total_eur)}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="cyber-generate-btn shrink-0 px-5 py-2.5 text-xs disabled:opacity-50"
          disabled={syncing}
          onClick={onSyncAll}
        >
          {syncing ? "Sync en cours…" : "Sync tout"}
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {dashboard.services.map((svc) => {
          const bal = balanceOf(svc);
          const alertLvl = thresholdAlertLevel(bal, svc.thresholds);
          return (
            <article
              key={svc.id}
              className="rounded-lg border-2 bg-cyber-surface/90 p-4 backdrop-blur-sm transition hover:brightness-110"
              style={serviceBorderStyle(svc.color)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl" aria-hidden>
                    {svc.icon || "◆"}
                  </span>
                  <div>
                    <h3 className="font-semibold text-cyber-text">{svc.name}</h3>
                    <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                      {svc.id}
                    </p>
                  </div>
                </div>
                <span title={svc.ping_ok ? "Service joignable" : "Ping échoué"}>
                  {svc.ping_ok ? "🟢" : "🔴"}
                </span>
              </div>
              <p className="mt-3 font-mono text-xl font-bold text-cyber-neon">
                {formatEur(bal)}
              </p>
              {alertLvl ? (
                <span
                  className={`mt-2 inline-block rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${alertBadgeClass(alertLvl)}`}
                >
                  Seuil {alertLvl}
                </span>
              ) : (
                <span className="mt-2 inline-block text-[10px] text-cyber-muted">
                  Solde OK
                </span>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}

// --- Wallet ---

function TopupModal({
  service,
  open,
  onClose,
  onSuccess,
}: {
  service: CockpitService | null;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setAmount("");
      setDescription("");
      setConfirmed(false);
      setError(null);
    }
  }, [open, service?.id]);

  if (!open || !service) return null;

  const parsed = parseFloat(amount.replace(",", "."));
  const validAmount = Number.isFinite(parsed) && parsed > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validAmount || !confirmed) return;
    setBusy(true);
    setError(null);
    const res = await topupCockpitService(service!.id, {
      amount_eur: parsed,
      description: description.trim() || undefined,
    });
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Recharge refusée."));
      return;
    }
    onSuccess();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="topup-title"
    >
      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="cyber-panel w-full max-w-md border-cyber-violet/40"
        style={serviceBorderStyle(service.color)}
      >
        <h2 id="topup-title" className="text-lg font-semibold text-cyber-text">
          Recharger — {service.name}
        </h2>
        <p className="mt-1 text-xs text-cyber-muted">
          Solde actuel : {formatEur(balanceOf(service))}
        </p>
        {error ? <ErrorBanner message={error} /> : null}
        <label className="mt-4 block space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
            Montant (€)
          </span>
          <input
            type="number"
            min={0.01}
            step={0.01}
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="cyber-prompt-field min-h-0"
            placeholder="50.00"
          />
        </label>
        <label className="mt-3 block space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
            Description (optionnel)
          </span>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="cyber-prompt-field min-h-0"
            placeholder="Recharge manuelle"
          />
        </label>
        <label className="mt-4 flex cursor-pointer items-start gap-2 text-sm text-cyber-text">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="mt-1"
          />
          <span>
            Je confirme l&apos;ajout de{" "}
            <strong>{validAmount ? formatEur(parsed) : "…"}</strong> au solde de{" "}
            <strong>{service.name}</strong>.
          </span>
        </label>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="cyber-action-btn" onClick={onClose}>
            Annuler
          </button>
          <button
            type="submit"
            className="cyber-action-btn cyber-action-btn-primary"
            disabled={busy || !validAmount || !confirmed}
          >
            {busy ? "Envoi…" : "Confirmer la recharge"}
          </button>
        </div>
      </form>
    </div>
  );
}

function WalletSection({
  services,
  onRefresh,
}: {
  services: CockpitService[];
  onRefresh: () => void;
}) {
  const [topupTarget, setTopupTarget] = useState<CockpitService | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [txFilter, setTxFilter] = useState<"" | TransactionType>("");
  const [transactions, setTransactions] = useState<CockpitTransaction[]>([]);
  const [txLoading, setTxLoading] = useState(false);
  const [txError, setTxError] = useState<string | null>(null);

  const selected = services.find((s) => s.id === selectedId) ?? services[0] ?? null;

  useEffect(() => {
    if (services.length && !selectedId) {
      setSelectedId(services[0].id);
    }
  }, [services, selectedId]);

  const loadTransactions = useCallback(async () => {
    if (!selected) return;
    setTxLoading(true);
    setTxError(null);
    const res = await fetchCockpitTransactions(selected.id, {
      limit: 20,
      type: txFilter || undefined,
    });
    setTxLoading(false);
    if (!res.ok) {
      setTxError(apiErrorMessage(res, "Impossible de charger l'historique."));
      setTransactions([]);
      return;
    }
    setTransactions(res.data ?? []);
  }, [selected, txFilter]);

  useEffect(() => {
    void loadTransactions();
  }, [loadTransactions]);

  return (
    <div className="space-y-6">
      <TopupModal
        service={topupTarget}
        open={topupTarget !== null}
        onClose={() => setTopupTarget(null)}
        onSuccess={() => {
          onRefresh();
          void loadTransactions();
        }}
      />

      <div className="cyber-panel overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead>
            <tr className="border-b border-cyber-border text-[10px] uppercase tracking-wider text-cyber-muted">
              <th className="py-2 pr-4">Service</th>
              <th className="py-2 pr-4">Solde</th>
              <th className="py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {services.map((svc) => (
              <tr
                key={svc.id}
                className="border-b border-cyber-border/60 hover:bg-cyber-bg/40"
              >
                <td className="py-3 pr-4">
                  <span className="mr-2">{svc.icon || "◆"}</span>
                  {svc.name}
                </td>
                <td className="py-3 pr-4 font-mono text-cyber-neon">
                  {formatEur(balanceOf(svc))}
                </td>
                <td className="py-3">
                  <button
                    type="button"
                    className="cyber-action-btn cyber-action-btn-primary"
                    onClick={() => setTopupTarget(svc)}
                  >
                    Recharger
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected ? (
        <div className="cyber-panel">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-semibold text-cyber-text">
              Historique — {selected.name}
            </h3>
            <div className="flex gap-2">
              {(["", "expense", "topup"] as const).map((f) => (
                <button
                  key={f || "all"}
                  type="button"
                  className={`cyber-action-btn text-[10px] ${
                    txFilter === f ? "cyber-action-btn-primary" : ""
                  }`}
                  onClick={() => setTxFilter(f)}
                >
                  {f === "" ? "Tout" : f === "expense" ? "Dépenses" : "Recharges"}
                </button>
              ))}
            </div>
          </div>
          {txError ? <ErrorBanner message={txError} /> : null}
          {txLoading ? (
            <p className="text-sm text-cyber-muted">Chargement…</p>
          ) : transactions.length === 0 ? (
            <p className="text-sm text-cyber-muted">Aucune transaction.</p>
          ) : (
            <ul className="space-y-2">
              {transactions.map((tx) => (
                <li
                  key={tx.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-cyber-border bg-cyber-bg/50 px-3 py-2 text-sm"
                >
                  <div>
                    <span
                      className={
                        tx.type === "topup" ? "text-cyber-neon" : "text-orange-300"
                      }
                    >
                      {tx.type === "topup" ? "+" : "−"}
                      {formatEur(tx.amount_eur)}
                    </span>
                    <span className="ml-2 text-cyber-muted">
                      {tx.description || tx.type}
                    </span>
                  </div>
                  <time className="text-[10px] text-cyber-muted">
                    {new Date(tx.created_at).toLocaleString("fr-FR")}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

// --- Seuils ---

function ThresholdsSection({
  services,
  onRefresh,
}: {
  services: CockpitService[];
  onRefresh: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, CockpitThresholds>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const next: Record<string, CockpitThresholds> = {};
    for (const s of services) {
      next[s.id] = { ...s.thresholds };
    }
    setDrafts(next);
  }, [services]);

  function updateDraft(
    id: string,
    field: keyof CockpitThresholds,
    value: string,
  ) {
    const num = parseFloat(value.replace(",", "."));
    setDrafts((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: Number.isFinite(num) ? num : 0,
      },
    }));
  }

  async function save(id: string) {
    const d = drafts[id];
    if (!d) return;
    setSavingId(id);
    setError(null);
    const res = await updateCockpitThresholds(id, {
      warning_eur: d.warning_eur,
      critical_eur: d.critical_eur,
      urgent_eur: d.urgent_eur,
    });
    setSavingId(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Échec de la sauvegarde."));
      return;
    }
    onRefresh();
  }

  return (
    <div className="space-y-4">
      {error ? <ErrorBanner message={error} /> : null}
      <div className="cyber-panel overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-cyber-border text-[10px] uppercase tracking-wider text-cyber-muted">
              <th className="py-2 pr-4">Service</th>
              <th className="py-2 pr-4">Warning (€)</th>
              <th className="py-2 pr-4">Critical (€)</th>
              <th className="py-2 pr-4">Urgent (€)</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {services.map((svc) => {
              const d = drafts[svc.id] ?? svc.thresholds;
              return (
                <tr
                  key={svc.id}
                  className="border-b border-cyber-border/60"
                  style={serviceBorderStyle(svc.color)}
                >
                  <td className="py-3 pr-4 font-medium">
                    {svc.icon} {svc.name}
                  </td>
                  {(["warning_eur", "critical_eur", "urgent_eur"] as const).map(
                    (field) => (
                      <td key={field} className="py-3 pr-4">
                        <input
                          type="number"
                          min={0}
                          step={0.5}
                          value={d[field]}
                          onChange={(e) => updateDraft(svc.id, field, e.target.value)}
                          className="cyber-prompt-field min-h-0 w-24 font-mono text-sm"
                        />
                      </td>
                    ),
                  )}
                  <td className="py-3">
                    <button
                      type="button"
                      className="cyber-action-btn cyber-action-btn-primary"
                      disabled={savingId === svc.id}
                      onClick={() => void save(svc.id)}
                    >
                      {savingId === svc.id ? "…" : "Sauver"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- Paramètres ---

function SettingsSection({
  services,
  onRefresh,
}: {
  services: CockpitService[];
  onRefresh: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [apiKeyEnv, setApiKeyEnv] = useState("");
  const [connector, setConnector] = useState("manual");
  const [color, setColor] = useState("#06b6d4");
  const [icon, setIcon] = useState("◆");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await createCockpitService({
      name: name.trim(),
      api_key_env: apiKeyEnv.trim(),
      connector: connector || "manual",
      color: color.trim() || null,
      icon: icon.trim() || null,
    });
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible d'ajouter le fournisseur."));
      return;
    }
    setShowForm(false);
    setName("");
    setApiKeyEnv("");
    onRefresh();
  }

  async function toggleEnabled(svc: CockpitService) {
    const res = await updateCockpitService(svc.id, { enabled: !svc.enabled });
    if (!res.ok) {
      setError(apiErrorMessage(res, "Mise à jour impossible."));
      return;
    }
    onRefresh();
  }

  async function handleDelete(svc: CockpitService) {
    const ok = window.confirm(
      `Supprimer le fournisseur « ${svc.name} » ? Cette action est irréversible.`,
    );
    if (!ok) return;
    const res = await deleteCockpitService(svc.id);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Suppression impossible."));
      return;
    }
    onRefresh();
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorBanner message={error} /> : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Fermer le formulaire" : "Ajouter un fournisseur"}
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={(e) => void handleCreate(e)}
          className="cyber-panel grid gap-4 sm:grid-cols-2"
        >
          <label className="block space-y-1 sm:col-span-2">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Nom
            </span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="cyber-prompt-field min-h-0"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Variable d&apos;env (clé API)
            </span>
            <input
              required
              value={apiKeyEnv}
              onChange={(e) => setApiKeyEnv(e.target.value)}
              className="cyber-prompt-field min-h-0 font-mono"
              placeholder="MY_API_KEY"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Connecteur
            </span>
            <select
              value={connector}
              onChange={(e) => setConnector(e.target.value)}
              className="cyber-prompt-field min-h-0"
            >
              {COCKPIT_CONNECTOR_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Couleur
            </span>
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="h-10 w-full cursor-pointer rounded border border-cyber-border bg-cyber-bg"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Icône (emoji)
            </span>
            <input
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="cyber-prompt-field min-h-0"
              maxLength={4}
            />
          </label>
          <div className="flex justify-end sm:col-span-2">
            <button
              type="submit"
              className="cyber-generate-btn px-5 py-2 text-xs"
              disabled={busy}
            >
              {busy ? "Création…" : "Créer le fournisseur"}
            </button>
          </div>
        </form>
      ) : null}

      <div className="space-y-3">
        {services.map((svc) => (
          <div
            key={svc.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 bg-cyber-surface/80 px-4 py-3"
            style={serviceBorderStyle(svc.color)}
          >
            <div>
              <p className="font-semibold text-cyber-text">
                {svc.icon} {svc.name}
              </p>
              <p className="text-xs text-cyber-muted">
                Connecteur : {svc.connector || "—"} · {svc.api_key_env}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className={`cyber-action-btn text-[10px] ${
                  svc.enabled ? "border-cyber-neon/50 text-cyber-neon" : ""
                }`}
                onClick={() => void toggleEnabled(svc)}
              >
                {svc.enabled ? "Activé" : "Désactivé"}
              </button>
              <button
                type="button"
                className="cyber-action-btn border-red-500/40 text-red-300 hover:border-red-400"
                onClick={() => void handleDelete(svc)}
              >
                Supprimer
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Cockpit financier — dashboard, wallet, seuils et paramètres fournisseurs.
 */
export function CockpitPage() {
  const [section, setSection] = useState<CockpitSection>("dashboard");
  const [dashboard, setDashboard] = useState<CockpitDashboard | null>(null);
  const [services, setServices] = useState<CockpitService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [dismissingAlerts, setDismissingAlerts] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [dashRes, svcRes] = await Promise.all([
      fetchCockpitDashboard(),
      fetchCockpitServices(),
    ]);
    setLoading(false);
    if (!dashRes.ok) {
      setError(apiErrorMessage(dashRes, "Impossible de charger le dashboard."));
      return;
    }
    if (!svcRes.ok) {
      setError(apiErrorMessage(svcRes, "Impossible de charger les services."));
      return;
    }
    setDashboard(dashRes.data ?? null);
    setServices(svcRes.data ?? []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const serviceList = useMemo(() => {
    if (services.length) return services;
    return dashboard?.services ?? [];
  }, [services, dashboard]);

  async function handleSyncAll() {
    setSyncing(true);
    setError(null);
    const res = await syncAllCockpitServices();
    setSyncing(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Sync globale échouée."));
      return;
    }
    await load();
  }

  async function handleDismissAlerts() {
    setDismissingAlerts(true);
    const res = await markCockpitAlertsRead();
    setDismissingAlerts(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de marquer les alertes."));
      return;
    }
    await load();
  }

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
          FinOps
        </p>
        <h1 className="cyber-glitch-title mt-1 text-2xl font-bold text-cyber-text md:text-3xl">
          Cockpit
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Soldes fournisseurs, recharges, seuils d&apos;alerte et synchronisation API.
        </p>
      </header>

      <SubTabs current={section} onChange={setSection} />

      {error ? <ErrorBanner message={error} /> : null}
      {loading && !dashboard ? <LoadingBlock /> : null}

      {!loading && section === "dashboard" && dashboard ? (
        <DashboardSection
          dashboard={dashboard}
          syncing={syncing}
          onSyncAll={() => void handleSyncAll()}
          onDismissAlerts={() => void handleDismissAlerts()}
          dismissingAlerts={dismissingAlerts}
        />
      ) : null}

      {!loading && section === "wallet" ? (
        <WalletSection services={serviceList} onRefresh={() => void load()} />
      ) : null}

      {!loading && section === "thresholds" ? (
        <ThresholdsSection
          services={serviceList}
          onRefresh={() => void load()}
        />
      ) : null}

      {!loading && section === "settings" ? (
        <SettingsSection services={serviceList} onRefresh={() => void load()} />
      ) : null}
    </div>
  );
}
