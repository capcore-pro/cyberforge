import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { GHOST_BTN, TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import {
  acknowledgeMonitoringAlert,
  fetchMonitoringAlerts,
  fetchMonitoringHealth,
  fetchMonitoringIncidents,
  formatUsdEur,
  overallStatusBadgeClass,
  resolveMonitoringAlert,
  resolveMonitoringIncident,
  runMonitoringCheck,
  severityBadgeClass,
  type MonitoringAlert,
  type MonitoringHealth,
  type MonitoringIncident,
  type OverallStatus,
} from "@/lib/monitoring-api";

type MonitoringTab = "global" | "alerts" | "incidents";
type AlertStatusFilter = "all" | "open" | "acknowledged" | "resolved";
type AlertSeverityFilter = "all" | "critical" | "warning" | "info";

const TABS: { id: MonitoringTab; label: string }[] = [
  { id: "global", label: "Vue globale" },
  { id: "alerts", label: "Alertes" },
  { id: "incidents", label: "Incidents" },
];

const STATUS_FILTERS: { id: AlertStatusFilter; label: string }[] = [
  { id: "all", label: "Toutes" },
  { id: "open", label: "Ouvertes" },
  { id: "acknowledged", label: "Acquittées" },
  { id: "resolved", label: "Résolues" },
];

const SEVERITY_FILTERS: { id: AlertSeverityFilter; label: string }[] = [
  { id: "all", label: "Toutes" },
  { id: "critical", label: "Critique" },
  { id: "warning", label: "Warning" },
  { id: "info", label: "Info" },
];

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const deltaMs = Date.now() - date.getTime();
  if (!Number.isFinite(deltaMs)) return iso;
  const mins = Math.max(0, Math.round(deltaMs / 60_000));
  if (mins < 60) return `il y a ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return `il y a ${Math.round(hours / 24)} j`;
}

function overallStatusLabel(status: OverallStatus): string {
  if (status === "healthy") return "Sain";
  if (status === "degraded") return "Dégradé";
  return "Critique";
}

export function MonitoringPage() {
  const [tab, setTab] = useState<MonitoringTab>("global");
  const [health, setHealth] = useState<MonitoringHealth | null>(null);
  const [openAlerts, setOpenAlerts] = useState<MonitoringAlert[]>([]);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [incidents, setIncidents] = useState<MonitoringIncident[]>([]);
  const [statusFilter, setStatusFilter] = useState<AlertStatusFilter>("open");
  const [severityFilter, setSeverityFilter] =
    useState<AlertSeverityFilter>("all");
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});

  const loadGlobal = useCallback(async () => {
    const [h, open] = await Promise.all([
      fetchMonitoringHealth(),
      fetchMonitoringAlerts({ status: "open" }),
    ]);
    setHealth(h);
    setOpenAlerts(open);
  }, []);

  const loadAlerts = useCallback(async () => {
    const items = await fetchMonitoringAlerts({
      status: statusFilter,
      severity: severityFilter === "all" ? undefined : severityFilter,
    });
    setAlerts(items);
  }, [severityFilter, statusFilter]);

  const loadIncidents = useCallback(async () => {
    const items = await fetchMonitoringIncidents("open");
    setIncidents(items);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await loadGlobal();
      await loadAlerts();
      await loadIncidents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, [loadAlerts, loadGlobal, loadIncidents]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (tab === "alerts") {
      void loadAlerts();
    }
  }, [tab, loadAlerts]);

  const agentPct = useMemo(() => {
    if (!health?.agents.total) return 0;
    return Math.round((health.agents.active / health.agents.total) * 100);
  }, [health]);

  async function handleCheck() {
    setChecking(true);
    setError(null);
    try {
      await runMonitoringCheck();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checks impossible.");
    } finally {
      setChecking(false);
    }
  }

  async function handleAckAlert(id: string) {
    setActionId(id);
    try {
      await acknowledgeMonitoringAlert(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible.");
    } finally {
      setActionId(null);
    }
  }

  async function handleResolveAlert(id: string) {
    setActionId(id);
    try {
      await resolveMonitoringAlert(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible.");
    } finally {
      setActionId(null);
    }
  }

  async function handleResolveIncident(id: string) {
    setActionId(id);
    try {
      await resolveMonitoringIncident(id, resolveNotes[id] || undefined);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible.");
    } finally {
      setActionId(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
            <i className="ti ti-activity text-base" aria-hidden />
            Infrastructure
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-white">
            <i className="ti ti-activity text-[#d4a843]" aria-hidden />
            Monitoring Center
          </h1>
          <p className="mt-2 text-sm text-white/50">
            Santé système, alertes pipeline et gestion des incidents
          </p>
        </div>
        {health ? (
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${overallStatusBadgeClass(health.overall_status)}`}
          >
            {overallStatusLabel(health.overall_status)}
          </span>
        ) : null}
      </header>

      <nav className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`${TAB_BASE} rounded-control ${tab === t.id ? TAB_ACTIVE : ""}`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error ? (
        <p className="rounded-control border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-white/50 animate-pulse">Chargement…</p>
      ) : tab === "global" ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <HealthCard
              title="API Backend"
              icon="ti ti-server"
              primary={health?.api.status === "online" ? "En ligne" : "Hors ligne"}
              secondary={`${health?.api.latency_ms ?? 0} ms`}
            />
            <HealthCard
              title="Agents"
              icon="ti ti-robot"
              primary={`${health?.agents.active ?? 0}/${health?.agents.total ?? 0} actifs`}
              secondary={
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full bg-teal-400"
                    style={{ width: `${agentPct}%` }}
                  />
                </div>
              }
            />
            <HealthCard
              title="Pipeline 30j"
              icon="ti ti-heart-rate-monitor"
              primary={`${Math.round((health?.pipeline.pass_rate ?? 0) * 100)}% validation`}
              secondary={`Score ${Math.round(health?.pipeline.avg_quality_score ?? 0)}/100`}
            />
            <HealthCard
              title="Coûts"
              icon="ti ti-coin"
              primary={`Jour ${formatUsdEur(health?.costs.today_usd ?? 0)}`}
              secondary={`Mois ${formatUsdEur(health?.costs.month_usd ?? 0)}`}
            />
          </div>

          <section className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-white/40">
              Alertes ouvertes
            </h2>
            {openAlerts.length === 0 ? (
              <p className="text-sm text-white/50">Aucune alerte ouverte.</p>
            ) : (
              <div className="space-y-3">
                {openAlerts.map((alert) => (
                  <AlertRow
                    key={alert.id}
                    alert={alert}
                    actionId={actionId}
                    onAck={() => void handleAckAlert(alert.id)}
                    showResolve={false}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      ) : tab === "alerts" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-1">
              {STATUS_FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setStatusFilter(f.id)}
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                    statusFilter === f.id
                      ? "border-cf-gold/40 bg-cf-gold/15 text-cf-gold"
                      : "border-white/10 bg-white/5 text-white/50"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={GHOST_BTN}
              disabled={checking}
              onClick={() => void handleCheck()}
            >
              {checking ? "Checks…" : "Lancer les checks"}
            </button>
          </div>

          <div className="flex flex-wrap gap-1">
            {SEVERITY_FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setSeverityFilter(f.id)}
                className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                  severityFilter === f.id
                    ? "border-white/25 bg-white/10 text-white"
                    : "border-white/10 bg-white/5 text-white/45"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {alerts.length === 0 ? (
            <p className="text-sm text-white/50">Aucune alerte pour ces filtres.</p>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  actionId={actionId}
                  onAck={() => void handleAckAlert(alert.id)}
                  onResolve={() => void handleResolveAlert(alert.id)}
                  showResolve={alert.status !== "resolved"}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <section className="space-y-3">
          {incidents.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6 text-center">
              <p className="text-sm text-teal-200">
                Aucun incident — système opérationnel ✓
              </p>
            </div>
          ) : (
            incidents.map((incident) => (
              <article
                key={incident.id}
                className="rounded-xl border border-white/10 bg-white/[0.03] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-semibold text-white">
                        {incident.title}
                      </h3>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${severityBadgeClass(incident.severity)}`}
                      >
                        {incident.severity}
                      </span>
                    </div>
                    {incident.description ? (
                      <p className="mt-1 text-sm text-white/60">
                        {incident.description}
                      </p>
                    ) : null}
                    <p className="mt-2 text-[11px] text-white/40">
                      {incident.source ?? "—"} ·{" "}
                      {formatRelativeTime(incident.detected_at)}
                    </p>
                  </div>
                </div>
                <textarea
                  className="mt-3 w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30"
                  rows={2}
                  placeholder="Notes de résolution…"
                  value={resolveNotes[incident.id] ?? ""}
                  onChange={(e) =>
                    setResolveNotes((prev) => ({
                      ...prev,
                      [incident.id]: e.target.value,
                    }))
                  }
                />
                <button
                  type="button"
                  className="mt-2 rounded-control border border-cf-gold/40 bg-cf-gold/15 px-3 py-1.5 text-xs font-semibold text-cf-gold hover:bg-cf-gold/25 disabled:opacity-50"
                  disabled={actionId === incident.id}
                  onClick={() => void handleResolveIncident(incident.id)}
                >
                  Résoudre
                </button>
              </article>
            ))
          )}
        </section>
      )}
    </div>
  );
}

function HealthCard({
  title,
  icon,
  primary,
  secondary,
}: {
  title: string;
  icon: string;
  primary: string;
  secondary: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center gap-2 text-[#d4a843]">
        <i className={icon} aria-hidden />
        <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/40">
          {title}
        </span>
      </div>
      <p className="mt-2 text-lg font-semibold text-white">{primary}</p>
      <div className="mt-1 text-sm text-white/50">{secondary}</div>
    </div>
  );
}

function AlertRow({
  alert,
  actionId,
  onAck,
  onResolve,
  showResolve,
}: {
  alert: MonitoringAlert;
  actionId: string | null;
  onAck: () => void;
  onResolve?: () => void;
  showResolve: boolean;
}) {
  return (
    <article className="flex flex-wrap items-start justify-between gap-3 rounded-control border border-white/10 bg-white/5 p-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-white">{alert.title}</h3>
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${severityBadgeClass(alert.severity)}`}
          >
            {alert.severity}
          </span>
        </div>
        {alert.message ? (
          <p className="mt-1 text-sm text-white/60">{alert.message}</p>
        ) : null}
        <p className="mt-2 text-[11px] text-white/40">
          {alert.source ?? "—"} · {formatRelativeTime(alert.created_at)}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        {alert.status === "open" ? (
          <button
            type="button"
            className={GHOST_BTN}
            disabled={actionId === alert.id}
            onClick={onAck}
          >
            Acquitter
          </button>
        ) : null}
        {showResolve && onResolve ? (
          <button
            type="button"
            className="rounded-control border border-cf-gold/40 bg-cf-gold/15 px-3 py-1.5 text-xs font-semibold text-cf-gold hover:bg-cf-gold/25 disabled:opacity-50"
            disabled={actionId === alert.id}
            onClick={onResolve}
          >
            Résoudre
          </button>
        ) : null}
      </div>
    </article>
  );
}
