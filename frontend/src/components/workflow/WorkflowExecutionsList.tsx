import { useEffect, useState } from "react";
import { Badge, Card } from "@/components/ui";
import { USD_TO_EUR } from "@/lib/dashboard-api";
import {
  fetchWorkflowExecutions,
  type Workflow,
  type WorkflowExecution,
} from "@/lib/workflows-api";
import {
  formatDuration,
  formatRelativeTime,
} from "@/lib/project-analytics-api";

function formatCostEur(costUsd: number): string {
  const eur = costUsd * USD_TO_EUR;
  if (eur < 0.01 && costUsd > 0) return "< 0.01€";
  return `${eur.toFixed(2)}€`;
}

function truncateGenerationId(id: string): string {
  const trimmed = id.trim();
  if (trimmed.length <= 14) return trimmed;
  return `${trimmed.slice(0, 8)}…${trimmed.slice(-4)}`;
}

function statusVariant(
  status: string,
): "teal" | "amber" | "red" | "gray" {
  const normalized = status.toLowerCase();
  if (normalized === "completed") return "teal";
  if (normalized === "running" || normalized === "in_progress") return "amber";
  if (normalized === "failed") return "red";
  return "gray";
}

interface WorkflowExecutionsListProps {
  workflow: Workflow;
  onViewExecution: (execution: WorkflowExecution) => void;
}

export function WorkflowExecutionsList({
  workflow,
  onViewExecution,
}: WorkflowExecutionsListProps) {
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const items = await fetchWorkflowExecutions(workflow.workflow_id, 10);
      if (!cancelled) {
        setExecutions(items);
        setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [workflow.workflow_id]);

  if (loading) {
    return (
      <div className="space-y-3" aria-busy="true">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            key={index}
            className="h-24 animate-pulse rounded-card border border-white/10 bg-white/5"
          />
        ))}
      </div>
    );
  }

  if (executions.length === 0) {
    return (
      <p className="rounded-card border border-white/10 bg-white/5 p-6 text-center text-sm text-white/45">
        Aucune exécution enregistrée pour ce workflow.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {executions.map((execution) => {
        const startedLabel = execution.started_at
          ? formatRelativeTime(execution.started_at)
          : "—";
        return (
          <Card key={execution.id} padding="md">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(execution.status)} dot>
                    {execution.status}
                  </Badge>
                  <span className="font-mono text-xs text-white/80">
                    {truncateGenerationId(execution.generation_id)}
                  </span>
                </div>
                <p className="text-xs text-white/45">
                  Démarré {startedLabel} · Durée :{" "}
                  {formatDuration(execution.duration_ms)}
                </p>
                <p className="text-xs text-white/55">
                  {execution.completed_steps}/{execution.total_steps} étapes ·{" "}
                  {formatCostEur(execution.total_cost_usd)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onViewExecution(execution)}
                className="shrink-0 text-xs font-medium text-cf-gold transition hover:text-white"
              >
                Voir le graphe →
              </button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
