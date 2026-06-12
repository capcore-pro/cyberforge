import { describe, expect, it } from "vitest";
import {
  resolveStepStatus,
  stepsToEdges,
  stepsToNodes,
} from "./workflow-graph";
import type { WorkflowExecution, WorkflowStep } from "./workflows-api";

const VITRINE_STEPS: WorkflowStep[] = [
  {
    id: "step-1",
    workflow_id: "wf-uuid",
    step_name: "BriefAI",
    step_type: "agent",
    agent_id: "brief",
    tool_id: null,
    execution_order: 1,
    is_optional: false,
    condition_field: null,
    condition_values: [],
  },
  {
    id: "step-2",
    workflow_id: "wf-uuid",
    step_name: "DesignSystemAI",
    step_type: "agent",
    agent_id: "design_system",
    tool_id: null,
    execution_order: 2,
    is_optional: false,
    condition_field: null,
    condition_values: [],
  },
  {
    id: "step-3",
    workflow_id: "wf-uuid",
    step_name: "GeneratorAI",
    step_type: "agent",
    agent_id: "generator",
    tool_id: null,
    execution_order: 3,
    is_optional: false,
    condition_field: null,
    condition_values: [],
  },
  {
    id: "step-4",
    workflow_id: "wf-uuid",
    step_name: "SupervisorAI",
    step_type: "agent",
    agent_id: "supervisor",
    tool_id: null,
    execution_order: 4,
    is_optional: false,
    condition_field: null,
    condition_values: [],
  },
  {
    id: "step-5",
    workflow_id: "wf-uuid",
    step_name: "DeployAI",
    step_type: "agent",
    agent_id: "deploy",
    tool_id: null,
    execution_order: 5,
    is_optional: false,
    condition_field: null,
    condition_values: [],
  },
];

describe("workflow-graph", () => {
  it("builds vitrine_simple graph with 5 nodes and 4 edges", () => {
    const nodes = stepsToNodes(VITRINE_STEPS);
    const edges = stepsToEdges(VITRINE_STEPS);

    expect(nodes).toHaveLength(5);
    expect(edges).toHaveLength(4);
    expect(nodes[0].type).toBe("agentNode");
    expect(nodes[0].position).toEqual({ x: 300, y: 0 });
    expect(nodes[4].position).toEqual({ x: 300, y: 480 });
    expect(edges[0].type).toBe("smoothstep");
    expect(edges[0].source).toBe("step-1");
    expect(edges[0].target).toBe("step-2");
  });

  it("marks all nodes completed when execution is completed", () => {
    const execution: WorkflowExecution = {
      id: "exec-1",
      workflow_id: "wf-uuid",
      generation_id: "gen-1",
      status: "completed",
      current_step: "DeployAI",
      completed_steps: 5,
      total_steps: 5,
      total_cost_usd: 0.09,
      total_tokens: 1000,
      duration_ms: 83_000,
      started_at: "2026-06-10T10:00:00Z",
      completed_at: "2026-06-10T10:01:23Z",
    };

    const nodes = stepsToNodes(VITRINE_STEPS, execution);
    expect(nodes.every((node) => node.data.status === "completed")).toBe(true);
  });

  it("marks running and pending nodes for in-progress execution", () => {
    const execution: WorkflowExecution = {
      id: "exec-2",
      workflow_id: "wf-uuid",
      generation_id: "gen-2",
      status: "running",
      current_step: "GeneratorAI",
      completed_steps: 3,
      total_steps: 5,
      total_cost_usd: 0.04,
      total_tokens: 500,
      duration_ms: 40_000,
      started_at: "2026-06-10T11:00:00Z",
      completed_at: null,
    };

    const byName = Object.fromEntries(
      stepsToNodes(VITRINE_STEPS, execution).map((node) => [
        node.data.label,
        node.data.status,
      ]),
    );

    expect(byName.BriefAI).toBe("completed");
    expect(byName.DesignSystemAI).toBe("completed");
    expect(byName.GeneratorAI).toBe("running");
    expect(byName.SupervisorAI).toBe("pending");
    expect(byName.DeployAI).toBe("pending");
    expect(resolveStepStatus(VITRINE_STEPS[2], VITRINE_STEPS, execution)).toBe(
      "running",
    );
  });
});
