import type { Edge, Node } from "@xyflow/react";
import type { WorkflowExecution, WorkflowStep } from "@/lib/workflows-api";

export type AgentNodeStatus =
  | "idle"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export interface AgentNodeData extends Record<string, unknown> {
  label: string;
  agent_id: string | null;
  step_type: string;
  is_optional: boolean;
  icon: string;
  color: string;
  status: AgentNodeStatus;
}

export const AGENT_ICONS: Record<string, string> = {
  brief: "ti-file-text",
  design_system: "ti-palette",
  database: "ti-database",
  auth: "ti-lock",
  payment: "ti-credit-card",
  generator: "ti-wand",
  supervisor: "ti-shield-check",
  deploy: "ti-rocket",
  extension_builder: "ti-puzzle",
  email: "ti-mail",
  media: "ti-photo",
};

export const AGENT_COLORS: Record<string, string> = {
  brief: "#6366f1",
  design_system: "#d4a843",
  database: "#0ea5e9",
  auth: "#8b5cf6",
  payment: "#10b981",
  generator: "#d4a843",
  supervisor: "#f59e0b",
  deploy: "#06b6d4",
  extension_builder: "#a855f7",
};

const NODE_X = 300;
const NODE_Y_GAP = 120;

function sortedSteps(steps: WorkflowStep[]): WorkflowStep[] {
  return [...steps].sort((a, b) => a.execution_order - b.execution_order);
}

export function resolveStepStatus(
  step: WorkflowStep,
  steps: WorkflowStep[],
  execution?: WorkflowExecution,
): AgentNodeStatus {
  if (!execution) return "idle";

  const status = execution.status.toLowerCase();
  if (status === "completed") return "completed";

  const order = step.execution_order;
  const completed = execution.completed_steps;
  const current = execution.current_step?.trim() ?? "";

  if (status === "failed") {
    if (order < completed) return "completed";
    if (step.step_name === current || order === completed) return "failed";
    const lastCompleted = sortedSteps(steps).find(
      (item) => item.execution_order === completed,
    );
    if (lastCompleted && step.step_name === lastCompleted.step_name) {
      return "failed";
    }
    return "pending";
  }

  if (step.step_name === current) return "running";
  if (order < completed) return "completed";
  return "pending";
}

function edgeStrokeForStatus(status: AgentNodeStatus): string {
  if (status === "running") return "#fbbf24";
  if (status === "completed") return "#14b8a6";
  if (status === "failed") return "#ef4444";
  return "rgba(255,255,255,0.2)";
}

export function stepsToNodes(
  steps: WorkflowStep[],
  execution?: WorkflowExecution,
): Node<AgentNodeData>[] {
  const ordered = sortedSteps(steps);

  return ordered.map((step, index) => {
    const agentId = step.agent_id?.trim() ?? "";
    return {
      id: step.id,
      type: "agentNode",
      position: { x: NODE_X, y: index * NODE_Y_GAP },
      data: {
        label: step.step_name,
        agent_id: step.agent_id,
        step_type: step.step_type,
        is_optional: step.is_optional,
        icon: AGENT_ICONS[agentId] ?? "ti-cpu",
        color: AGENT_COLORS[agentId] ?? "#888888",
        status: resolveStepStatus(step, ordered, execution),
      },
    };
  });
}

export function stepsToEdges(
  steps: WorkflowStep[],
  execution?: WorkflowExecution,
): Edge[] {
  const ordered = sortedSteps(steps);
  const edges: Edge[] = [];

  for (let i = 0; i < ordered.length - 1; i += 1) {
    const sourceStep = ordered[i];
    const targetStep = ordered[i + 1];
    const sourceStatus = resolveStepStatus(sourceStep, ordered, execution);

    edges.push({
      id: `e-${sourceStep.id}-${targetStep.id}`,
      source: sourceStep.id,
      target: targetStep.id,
      type: "smoothstep",
      animated: sourceStatus === "running",
      style: {
        strokeWidth: 2,
        stroke: edgeStrokeForStatus(sourceStatus),
      },
    });
  }

  return edges;
}
