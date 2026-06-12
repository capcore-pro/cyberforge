import { useCallback, useEffect, useState } from "react";
import { GHOST_BTN, TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import { WorkflowCanvas } from "@/components/workflow/WorkflowCanvas";
import { WorkflowCard } from "@/components/workflow/WorkflowCard";
import { WorkflowExecutionsList } from "@/components/workflow/WorkflowExecutionsList";
import {
  fetchWorkflow,
  fetchWorkflows,
  type Workflow,
  type WorkflowExecution,
} from "@/lib/workflows-api";

type WorkflowsView = "list" | "detail";
type DetailTab = "graph" | "executions";

export function WorkflowsPage() {
  const [view, setView] = useState<WorkflowsView>("list");
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("graph");
  const [selectedExecution, setSelectedExecution] =
    useState<WorkflowExecution | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchWorkflows();
      setWorkflows(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const activeCount = workflows.filter((w) => w.status === "active").length;

  async function openWorkflow(workflow: Workflow) {
    const detail = await fetchWorkflow(workflow.workflow_id);
    setSelectedWorkflow(detail ?? workflow);
    setSelectedExecution(null);
    setDetailTab("graph");
    setView("detail");
  }

  function handleBack() {
    setView("list");
    setSelectedWorkflow(null);
    setSelectedExecution(null);
    setDetailTab("graph");
  }

  function handleViewExecution(execution: WorkflowExecution) {
    setSelectedExecution(execution);
    setDetailTab("graph");
  }

  if (view === "detail" && selectedWorkflow) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <button type="button" onClick={handleBack} className={GHOST_BTN}>
          ← Retour
        </button>

        <header className="space-y-2">
          <h1 className="text-2xl font-semibold text-white">{selectedWorkflow.name}</h1>
          {selectedWorkflow.description ? (
            <p className="text-sm text-white/50">{selectedWorkflow.description}</p>
          ) : null}
        </header>

        <nav className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setDetailTab("graph")}
            className={`${TAB_BASE} rounded-control ${detailTab === "graph" ? TAB_ACTIVE : ""}`}
          >
            Graphe
          </button>
          <button
            type="button"
            onClick={() => setDetailTab("executions")}
            className={`${TAB_BASE} rounded-control ${detailTab === "executions" ? TAB_ACTIVE : ""}`}
          >
            Exécutions
          </button>
        </nav>

        {detailTab === "graph" ? (
          <div className="space-y-3">
            {selectedExecution ? (
              <p className="text-xs text-white/45">
                Exécution{" "}
                <span className="font-mono text-white/70">
                  {selectedExecution.generation_id}
                </span>{" "}
                · statut {selectedExecution.status}
              </p>
            ) : (
              <p className="text-xs text-white/45">
                Vue statique du pipeline (sans exécution active).
              </p>
            )}
            <WorkflowCanvas
              workflow={selectedWorkflow}
              execution={selectedExecution ?? undefined}
            />
          </div>
        ) : (
          <WorkflowExecutionsList
            workflow={selectedWorkflow}
            onViewExecution={handleViewExecution}
          />
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
            <i className="ti ti-git-branch text-base" aria-hidden />
            Pipeline V2
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-white">
            <i className="ti ti-git-branch text-[#d4a843]" aria-hidden />
            Workflows
          </h1>
          <p className="mt-2 text-sm text-white/50">
            Visualisation des pipelines de génération par type de projet.
          </p>
        </div>
        <span className="rounded-full border border-[#d4a843]/35 bg-[#d4a843]/10 px-3 py-1 text-xs font-semibold text-[#d4a843]">
          {activeCount} workflows actifs
        </span>
      </header>

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div
              key={index}
              className="h-40 animate-pulse rounded-card border border-white/10 bg-white/5"
            />
          ))}
        </div>
      ) : workflows.length === 0 ? (
        <p className="rounded-card border border-white/10 bg-white/5 p-8 text-center text-sm text-white/45">
          Aucun workflow disponible.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {workflows.map((workflow) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              onOpen={(item) => void openWorkflow(item)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
