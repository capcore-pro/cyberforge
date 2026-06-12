import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AgentNode } from "@/components/workflow/AgentNode";
import { stepsToEdges, stepsToNodes } from "@/lib/workflow-graph";
import type { Workflow, WorkflowExecution } from "@/lib/workflows-api";

const nodeTypes = { agentNode: AgentNode };

interface WorkflowCanvasProps {
  workflow: Workflow;
  execution?: WorkflowExecution;
}

export function WorkflowCanvas({ workflow, execution }: WorkflowCanvasProps) {
  const nodes = useMemo(
    () => stepsToNodes(workflow.steps, execution),
    [workflow.steps, execution],
  );
  const edges = useMemo(
    () => stepsToEdges(workflow.steps, execution),
    [workflow.steps, execution],
  );

  return (
    <div className="h-[min(70vh,500px)] w-full overflow-hidden rounded-card border border-white/10 bg-transparent">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
          panOnDrag
          zoomOnScroll
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
        >
          <Background color="rgba(255,255,255,0.03)" gap={24} />
          <Controls
            style={{
              background: "var(--cf-bg-card)",
              border: "1px solid var(--cf-border)",
            }}
          />
          <MiniMap
            nodeColor={(node) => String(node.data?.color ?? "#888888")}
            style={{ background: "var(--cf-bg-secondary)" }}
          />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
