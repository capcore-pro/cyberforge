import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Badge } from "@/components/ui";
import type { AgentNodeData } from "@/lib/workflow-graph";

function borderClass(status: AgentNodeData["status"]): string {
  if (status === "pending") return "border-white/20";
  if (status === "running") return "border-amber-400 animate-pulse";
  if (status === "completed") return "border-teal-500/50";
  if (status === "failed") return "border-red-500/50";
  return "border-white/10";
}

function statusBadge(status: AgentNodeData["status"]) {
  if (status === "pending") {
    return (
      <Badge variant="gray" size="sm">
        En attente
      </Badge>
    );
  }
  if (status === "running") {
    return (
      <Badge variant="amber" size="sm" dot pulse>
        En cours
      </Badge>
    );
  }
  if (status === "completed") {
    return (
      <Badge variant="teal" size="sm">
        ✓
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge variant="red" size="sm">
        ✗
      </Badge>
    );
  }
  return null;
}

export function AgentNode({ data }: NodeProps) {
  const node = data as AgentNodeData;
  const runningGlow =
    node.status === "running"
      ? { boxShadow: "0 0 18px rgba(251, 191, 36, 0.45)" }
      : undefined;

  return (
    <div
      className={`w-[200px] rounded-card border-2 bg-[var(--cf-bg-card)] ${borderClass(node.status)}`}
      style={runningGlow}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !border-white/30 !bg-white/20"
      />

      <div className="flex items-start justify-between gap-2 p-2">
        <div className="flex min-w-0 items-start gap-2">
          <i
            className={`ti ${node.icon} mt-0.5 shrink-0 text-base`}
            style={{ color: node.color }}
            aria-hidden
          />
          <p className="truncate text-sm font-medium text-white">{node.label}</p>
        </div>
        <div className="shrink-0">{statusBadge(node.status)}</div>
      </div>

      {node.is_optional ? (
        <div className="border-t border-white/5 px-2 py-1.5">
          <Badge variant="gray" size="sm">
            Optionnel
          </Badge>
        </div>
      ) : null}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !border-white/30 !bg-white/20"
      />
    </div>
  );
}
