import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { KnowledgeGraphNodeData } from "@/lib/knowledge-graph-layout";

export function KnowledgeGraphNode({ data, selected }: NodeProps) {
  const node = data as KnowledgeGraphNodeData;
  const color = node.color;

  return (
    <div
      className={`flex h-[50px] w-[160px] items-center justify-center rounded-md border-2 px-2 text-center text-xs font-medium text-white shadow-md transition ${
        selected ? "ring-2 ring-white/40" : ""
      }`}
      style={{
        backgroundColor: `${color}33`,
        borderColor: color,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !border-white/30 !bg-white/20"
      />
      <span className="line-clamp-2 leading-tight">{node.label}</span>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !border-white/30 !bg-white/20"
      />
    </div>
  );
}
