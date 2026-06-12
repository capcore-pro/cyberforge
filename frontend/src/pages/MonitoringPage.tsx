import { useCallback, useEffect, useState } from "react";
import { GHOST_BTN } from "@/components/settings/settings-theme";
import {
  acknowledgeMonitoringAlert,
  fetchMonitoringAlerts,
  fetchMonitoringIncidents,
  fetchMonitoringOverview,
  fetchMonitoringSources,
  resolveMonitoringAlert,
  resolveMonitoringIncident,
  runMonitoringScan,
  severityBadgeClass,
  type MonitoringAlert,
  type MonitoringIncident,
  type MonitoringOverview,
  type MonitoringSource,
} from "@/lib/monitoring-api";

type MonitoringTab = "overview" | "alerts" | "incidents";

const TABS: { id: MonitoringTab; label: string }[] = [
  { id: "overview", label: "Vue d'ensemble" },
  { id: "alerts", label: "Alertes" },
  { id: "incidents", label: "Incidents" },
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

export function MonitoringPage() {
  const [tab, setTab] = useState<MonitoringTab>("overview");
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);
  const [sources, setSources] = useState<MonitoringSource[]>([]);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [incidents, setIncidents] = useState<MonitoringIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, src, al, inc] = await Promise.all([
        fetchMonitoringOverview(),
        fetchMonitoringSources(),
        fetchMonitoringAlerts("open"),
        fetchMonitoringIncidents("open"),
      ]);
      setOverview(ov);
      setSources(src);
      setAlerts(al);
      setIncidents(inc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleScan() {
    setScanning(true);
    setError(null);
    try {
      await runMonitoringScan();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan impossible.");
    } finally {
      setScanning(false);
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
      await resolveMonitoringIncident(id, "Résolu depuis le Monitoring Center");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible.");
    } finally {
      setActionId(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
            Infrastructure
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-cf-text">
            Monitoring Center
          </h1>
          <p className="mt-2 text-sm text-cf-body">
            Alertes pipeline, incidents et sources de télémétrie
          </p>
        </div>
        <button
          type="button"
          className={GHOST_BTN}
          disabled={scanning}
          onClick={() => void handleScan()}
        >
          {scanning ? "Scan en cours…" : "Lancer un scan"}
        </button>
      </header>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={
              tab === t.id
                ? "rounded-control border border-cf-gold/40 bg-cf-gold/15 px-3 py-1.5 text-xs font-semibold text-cf-gold"
                : "rounded-control border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-cf-muted hover:text-cf-text"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="rounded-control border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-cf-muted animate-pulse">Chargement…</p>
      ) : tab === "overview" ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                label: "Alertes ouvertes",
                value: overview?.open_alerts_count ?? 0,
                icon: "ti ti-bell-ringing",
              },
              {
                label: "Critiques",
                value: overview?.critical_alerts_count ?? 0,
                icon: "ti ti-alert-triangle",
              },
              {
                label: "Incidents ouverts",
                value: overview?.open_incidents_count ?? 0,
                icon: "ti ti-flame",
              },
              {
                label: "Sources actives",
                value: overview?.sources_active ?? 0,
                icon: "ti ti-database",
              },
            ].map((card) => (
              <div
                key={card.label}
                className="rounded-card border border-white/10 bg-white/5 p-4 backdrop-blur-xl"
              >
                <div className="flex items-center gap-2 text-cf-gold">
                  <i className={card.icon} aria-hidden />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                    {card.label}
                  </span>
                </div>
                <p className="mt-2 text-3xl font-semibold tabular-nums text-cf-text">
                  {card.value}
                </p>
              </div>
            ))}
          </div>

          <section className="rounded-card border border-white/10 bg-white/5 p-5 backdrop-blur-xl">
            <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
              Sources de monitoring
            </h2>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {sources.map((src) => (
                <div
                  key={src.id}
                  className="flex items-center justify-between rounded-control border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium text-cf-text">
                      {src.source_name}
                    </p>
                    <p className="text-[11px] text-cf-muted">{src.source_type}</p>
                  </div>
                  <span className="rounded-full border border-teal-400/30 bg-teal-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-teal-200">
                    {src.status}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : tab === "alerts" ? (
        <section className="space-y-3">
          {alerts.length === 0 ? (
            <p className="text-sm text-cf-muted">Aucune alerte ouverte.</p>
          ) : (
            alerts.map((alert) => (
              <article
                key={alert.id}
                className="rounded-card border border-white/10 bg-white/5 p-4 backdrop-blur-xl"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-semibold text-cf-text">
                        {alert.title}
                      </h3>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${severityBadgeClass(alert.severity)}`}
                      >
                        {alert.severity}
                      </span>
                    </div>
                    {alert.message ? (
                      <p className="mt-1 text-sm text-cf-body">{alert.message}</p>
                    ) : null}
                    <p className="mt-2 text-[11px] text-cf-muted">
                      {alert.source ?? "—"} · {formatRelativeTime(alert.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      className={GHOST_BTN}
                      disabled={actionId === alert.id}
                      onClick={() => void handleAckAlert(alert.id)}
                    >
                      Accuser
                    </button>
                    <button
                      type="button"
                      className="rounded-control border border-cf-gold/40 bg-cf-gold/15 px-3 py-1.5 text-xs font-semibold text-cf-gold hover:bg-cf-gold/25 disabled:opacity-50"
                      disabled={actionId === alert.id}
                      onClick={() => void handleResolveAlert(alert.id)}
                    >
                      Résoudre
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>
      ) : (
        <section className="space-y-3">
          {incidents.length === 0 ? (
            <p className="text-sm text-cf-muted">Aucun incident ouvert.</p>
          ) : (
            incidents.map((incident) => (
              <article
                key={incident.id}
                className="rounded-card border border-white/10 bg-white/5 p-4 backdrop-blur-xl"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-semibold text-cf-text">
                        {incident.title}
                      </h3>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${severityBadgeClass(incident.severity)}`}
                      >
                        {incident.severity}
                      </span>
                    </div>
                    {incident.description ? (
                      <p className="mt-1 text-sm text-cf-body">
                        {incident.description}
                      </p>
                    ) : null}
                    <p className="mt-2 text-[11px] text-cf-muted">
                      {incident.source ?? "—"} ·{" "}
                      {formatRelativeTime(incident.detected_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded-control border border-cf-gold/40 bg-cf-gold/15 px-3 py-1.5 text-xs font-semibold text-cf-gold hover:bg-cf-gold/25 disabled:opacity-50"
                    disabled={actionId === incident.id}
                    onClick={() => void handleResolveIncident(incident.id)}
                  >
                    Résoudre
                  </button>
                </div>
              </article>
            ))
          )}
        </section>
      )}
    </div>
  );
}
