import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  step_name: string;
  step_type: string;
  agent_id: string | null;
  tool_id: string | null;
  execution_order: number;
  is_optional: boolean;
  condition_field: string | null;
  condition_values: string[];
}

export interface Workflow {
  id: string;
  workflow_id: string;
  name: string;
  description: string;
  workflow_type: string;
  project_types: string[];
  version: string;
  status: string;
  steps: WorkflowStep[];
  step_count: number;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  generation_id: string;
  status: string;
  current_step: string | null;
  completed_steps: number;
  total_steps: number;
  total_cost_usd: number;
  total_tokens: number;
  duration_ms: number;
  started_at: string;
  completed_at: string | null;
}

function safeNumber(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item));
}

function normalizeStep(row: Record<string, unknown>): WorkflowStep {
  return {
    id: String(row.id ?? ""),
    workflow_id: String(row.workflow_id ?? ""),
    step_name: String(row.step_name ?? ""),
    step_type: String(row.step_type ?? ""),
    agent_id: row.agent_id != null ? String(row.agent_id) : null,
    tool_id: row.tool_id != null ? String(row.tool_id) : null,
    execution_order: safeNumber(row.execution_order),
    is_optional: Boolean(row.is_optional),
    condition_field:
      row.condition_field != null ? String(row.condition_field) : null,
    condition_values: normalizeStringArray(row.condition_values),
  };
}

function normalizeWorkflow(row: Record<string, unknown>): Workflow {
  const stepsRaw = Array.isArray(row.steps) ? row.steps : [];
  const steps = stepsRaw
    .map((step) => normalizeStep(step as Record<string, unknown>))
    .sort((a, b) => a.execution_order - b.execution_order);

  return {
    id: String(row.id ?? ""),
    workflow_id: String(row.workflow_id ?? ""),
    name: String(row.name ?? ""),
    description: String(row.description ?? ""),
    workflow_type: String(row.workflow_type ?? ""),
    project_types: normalizeStringArray(row.project_types),
    version: String(row.version ?? ""),
    status: String(row.status ?? ""),
    steps,
    step_count: safeNumber(row.step_count ?? steps.length),
  };
}

function normalizeExecution(row: Record<string, unknown>): WorkflowExecution {
  return {
    id: String(row.id ?? ""),
    workflow_id: String(row.workflow_id ?? ""),
    generation_id: String(row.generation_id ?? ""),
    status: String(row.status ?? ""),
    current_step: row.current_step != null ? String(row.current_step) : null,
    completed_steps: safeNumber(row.completed_steps),
    total_steps: safeNumber(row.total_steps),
    total_cost_usd: safeNumber(row.total_cost_usd),
    total_tokens: safeNumber(row.total_tokens),
    duration_ms: safeNumber(row.duration_ms),
    started_at: String(row.started_at ?? ""),
    completed_at: row.completed_at != null ? String(row.completed_at) : null,
  };
}

export async function fetchWorkflows(): Promise<Workflow[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/workflows`,
  });
  if (!res.ok) return [];
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) => normalizeWorkflow(row as Record<string, unknown>));
}

export async function fetchWorkflow(workflowId: string): Promise<Workflow | null> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/workflows/${encodeURIComponent(workflowId)}`,
  });
  if (!res.ok) return null;
  return normalizeWorkflow(res.data ?? {});
}

export async function fetchWorkflowExecutions(
  workflowId: string,
  limit = 10,
): Promise<WorkflowExecution[]> {
  const res = await apiRequest<{ items?: unknown[] }>({
    method: "GET",
    path: `${API_PREFIX}/workflows/${encodeURIComponent(workflowId)}/executions?limit=${limit}`,
  });
  if (!res.ok) return [];
  const items = Array.isArray(res.data?.items) ? res.data.items : [];
  return items.map((row) => normalizeExecution(row as Record<string, unknown>));
}

export async function fetchExecutionByGeneration(
  generationId: string,
): Promise<WorkflowExecution | null> {
  const res = await apiRequest<Record<string, unknown>>({
    method: "GET",
    path: `${API_PREFIX}/workflows/execution/${encodeURIComponent(generationId)}`,
  });
  if (!res.ok) return null;
  return normalizeExecution(res.data ?? {});
}
