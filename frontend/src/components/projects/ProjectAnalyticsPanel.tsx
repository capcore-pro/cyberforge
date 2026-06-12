import { useEffect, useRef, useState, type ReactNode } from "react";
import { Badge, Card } from "@/components/ui";
import {
  auditEventIcon,
  auditEventLabel,
  fetchProjectAuditLog,
  fetchProjectLLMCost,
  fetchProjectQuality,
  fetchProjectWorkflowHistory,
  formatCostEur,
  formatDuration,
  formatRelativeTime,
  qualityBadgeVariant,
  type ProjectAuditEvent,
  type ProjectLLMCost,
  type ProjectQuality,
  type ProjectWorkflowSession,
  workflowStatusVariant,
} from "@/lib/project-analytics-api";

export interface ProjectAnalyticsPanelProps {
  project_id: string;
  generation_id?: string;
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Chargement analytics">
      <div className="h-4 w-32 animate-pulse rounded bg-white/10" />
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="h-16 animate-pulse rounded-card bg-white/5" />
        <div className="h-16 animate-pulse rounded-card bg-white/5" />
        <div className="h-16 animate-pulse rounded-card bg-white/5" />
      </div>
    </div>
  );
}

function KpiMetric({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 p-4 text-center">
      <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
        {label}
      </p>
      <div className="mt-2 flex flex-col items-center gap-1">
        {children ?? (
          <p className="text-lg font-semibold text-cf-text">{value}</p>
        )}
      </div>
    </div>
  );
}

function AgentCostBars({ cost }: { cost: ProjectLLMCost }) {
  const maxCost = Math.max(...cost.by_agent.map((a) => a.cost_usd), 0.0001);

  return (
    <Card title="Coût LLM par agent" padding="md">
      <div className="space-y-3">
        {cost.by_agent.map((agent) => {
          const width = Math.max(4, Math.round((agent.cost_usd / maxCost) * 100));
          return (
            <div key={agent.agent_name} className="space-y-1">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate text-cf-text">{agent.agent_name}</span>
                <span className="shrink-0 text-cf-muted">
                  {formatCostEur(agent.cost_usd)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-cf-gold/70"
                  style={{ width: `${width}%` }}
                  role="presentation"
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function WorkflowHistoryTable({ sessions }: { sessions: ProjectWorkflowSession[] }) {
  const rows = sessions.slice(0, 5);

  return (
    <Card title="Historique workflow" padding="md">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-left text-xs">
          <thead>
            <tr className="border-b border-white/10 text-cf-label">
              <th className="pb-2 pr-3 font-medium">Date</th>
              <th className="pb-2 pr-3 font-medium">Workflow</th>
              <th className="pb-2 pr-3 font-medium">Statut</th>
              <th className="pb-2 pr-3 font-medium">Agents</th>
              <th className="pb-2 font-medium">Coût</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((session) => {
              const statusVariant = workflowStatusVariant(session.status);
              const isRunning =
                session.status.toLowerCase() === "running" ||
                session.status.toLowerCase() === "in_progress";
              return (
                <tr
                  key={session.generation_id}
                  className="border-b border-white/5 last:border-0"
                >
                  <td className="py-2 pr-3 text-cf-muted">
                    {session.created_at
                      ? new Intl.DateTimeFormat("fr-FR", {
                          day: "2-digit",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        }).format(new Date(session.created_at))
                      : "—"}
                  </td>
                  <td className="py-2 pr-3 font-mono text-[11px] text-cf-text">
                    {session.workflow_id ?? "—"}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge variant={statusVariant} dot pulse={isRunning}>
                      {session.status}
                    </Badge>
                  </td>
                  <td className="py-2 pr-3 text-cf-text">
                    {session.agents_completed}/{session.total_agents || "—"}
                  </td>
                  <td className="py-2 text-cf-muted">
                    {session.total_cost_usd != null && session.total_cost_usd > 0
                      ? formatCostEur(session.total_cost_usd)
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function AuditTimeline({ events }: { events: ProjectAuditEvent[] }) {
  const rows = events.slice(0, 5);

  return (
    <Card title="Activité" padding="md">
      <ol className="space-y-4">
        {rows.map((event, index) => (
          <li key={`${event.event_type}-${event.created_at}-${index}`} className="flex gap-3">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-cf-border-input bg-cf-secondary/60">
              <i
                className={`ti ${auditEventIcon(event.event_type)} text-sm text-cf-gold`}
                aria-hidden
              />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-cf-text">{auditEventLabel(event.event_type)}</p>
              <p className="mt-0.5 text-[11px] text-cf-muted">
                {formatRelativeTime(event.created_at)}
                {event.actor_type ? ` · ${event.actor_type}` : ""}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function ProjectAnalyticsPanel({
  project_id,
  generation_id,
}: ProjectAnalyticsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [quality, setQuality] = useState<ProjectQuality | null>(null);
  const [llmCost, setLlmCost] = useState<ProjectLLMCost | null>(null);
  const [workflow, setWorkflow] = useState<ProjectWorkflowSession[]>([]);
  const [audit, setAudit] = useState<ProjectAuditEvent[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const [qualityRes, costRes, workflowRes, auditRes] = await Promise.all([
        fetchProjectQuality(project_id, generation_id),
        fetchProjectLLMCost(project_id, generation_id),
        fetchProjectWorkflowHistory(project_id),
        fetchProjectAuditLog(project_id),
      ]);

      if (cancelled) return;

      setQuality(qualityRes);
      setLlmCost(costRes);
      setWorkflow(workflowRes);
      setAudit(auditRes);
      setLoading(false);
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [project_id, generation_id]);

  const latestDurationMs =
    workflow.find((s) => s.duration_ms != null && s.duration_ms > 0)?.duration_ms ??
    null;

  const hasData =
    (quality != null && quality.score > 0) ||
    (llmCost != null && llmCost.total_cost_usd > 0) ||
    workflow.length > 0 ||
    audit.length > 0;

  if (loading) {
    return (
      <section className="space-y-4 rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
        <header className="flex items-center gap-2">
          <i className="ti ti-chart-bar text-lg text-cf-gold" aria-hidden />
          <h2 className="text-sm font-semibold text-cf-text">Analytics</h2>
        </header>
        <AnalyticsSkeleton />
      </section>
    );
  }

  if (!hasData) {
    return (
      <section className="space-y-4 rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
        <header className="flex items-center gap-2">
          <i className="ti ti-chart-bar text-lg text-cf-gold" aria-hidden />
          <h2 className="text-sm font-semibold text-cf-text">Analytics</h2>
        </header>
        <p className="text-sm text-cf-muted">
          Aucune donnée analytique disponible pour ce projet
        </p>
      </section>
    );
  }

  const qualityScore = quality?.score ?? 0;
  const totalCostUsd = llmCost?.total_cost_usd ?? 0;

  return (
    <section className="space-y-5 rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
      <header className="flex items-center gap-2">
        <i className="ti ti-chart-bar text-lg text-cf-gold" aria-hidden />
        <h2 className="text-sm font-semibold text-cf-text">Analytics</h2>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiMetric label="Score qualité" value="">
          {qualityScore > 0 ? (
            <Badge variant={qualityBadgeVariant(qualityScore)} size="md">
              {qualityScore}/100
            </Badge>
          ) : (
            <p className="text-lg font-semibold text-cf-muted">—</p>
          )}
        </KpiMetric>
        <KpiMetric
          label="Coût total"
          value={totalCostUsd > 0 ? formatCostEur(totalCostUsd) : "—"}
        />
        <KpiMetric label="Durée" value={formatDuration(latestDurationMs)} />
      </div>

      {llmCost && llmCost.by_agent.length > 0 ? (
        <AgentCostBars cost={llmCost} />
      ) : null}

      {workflow.length > 0 ? <WorkflowHistoryTable sessions={workflow} /> : null}

      {audit.length > 0 ? <AuditTimeline events={audit} /> : null}
    </section>
  );
}

export function LazyProjectAnalyticsPanel(props: ProjectAnalyticsPanelProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = rootRef.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} className="min-h-[1px]">
      {visible ? (
        <ProjectAnalyticsPanel {...props} />
      ) : (
        <div className="h-24 rounded-card border border-cf-border-input bg-cf-card/40" aria-hidden />
      )}
    </div>
  );
}
