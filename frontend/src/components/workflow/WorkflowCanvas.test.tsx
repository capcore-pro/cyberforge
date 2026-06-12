import { describe, expect, it, vi } from "vitest";
import { type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: { children?: ReactNode }) => (
    <div data-testid="react-flow">{children}</div>
  ),
  ReactFlowProvider: ({ children }: { children?: ReactNode }) => (
    <div>{children}</div>
  ),
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
}));

import { WorkflowCanvas } from "./WorkflowCanvas";
import type { Workflow } from "@/lib/workflows-api";

const WORKFLOW: Workflow = {
  id: "wf-uuid",
  workflow_id: "vitrine_simple",
  name: "Vitrine Simple",
  description: "Test",
  workflow_type: "generation",
  project_types: ["vitrine_next"],
  version: "2.0.0",
  status: "active",
  step_count: 2,
  steps: [
    {
      id: "s1",
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
      id: "s2",
      workflow_id: "wf-uuid",
      step_name: "DeployAI",
      step_type: "agent",
      agent_id: "deploy",
      tool_id: null,
      execution_order: 2,
      is_optional: false,
      condition_field: null,
      condition_values: [],
    },
  ],
};

describe("WorkflowCanvas", () => {
  it("mounts ReactFlow without crash", () => {
    const html = renderToStaticMarkup(<WorkflowCanvas workflow={WORKFLOW} />);
    expect(html).toContain('data-testid="react-flow"');
  });
});
