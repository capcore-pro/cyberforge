import type { Edge, Node } from "@xyflow/react";
import {
  ENTITY_TYPE_COLORS,
  graphNodeKey,
  type KnowledgeGraphEdge,
  type KnowledgeGraphNode,
} from "@/lib/knowledge-graph-api";

export interface KnowledgeGraphNodeData extends Record<string, unknown> {
  label: string;
  entity_type: string;
  entity_id: string;
  color: string;
  properties: Record<string, unknown>;
}

const TYPE_ORDER = [
  "workflow",
  "agent",
  "tool",
  "prompt",
  "project",
  "client",
  "document",
  "memory",
];

const COLUMN_GAP = 220;
const ROW_GAP = 70;
const COLUMN_BASE_X = 40;

export function layoutKnowledgeGraphNodes(
  nodes: KnowledgeGraphNode[],
): Node<KnowledgeGraphNodeData>[] {
  const counters = new Map<string, number>();

  return nodes.map((node) => {
    const entityType = String(node.entity_type);
    const typeIndex = Math.max(
      0,
      TYPE_ORDER.indexOf(entityType) >= 0
        ? TYPE_ORDER.indexOf(entityType)
        : TYPE_ORDER.length,
    );
    const row = counters.get(entityType) ?? 0;
    counters.set(entityType, row + 1);

    const color = ENTITY_TYPE_COLORS[entityType] ?? "#888888";

    return {
      id: graphNodeKey(entityType, String(node.entity_id)),
      type: "knowledgeGraphNode",
      position: {
        x: COLUMN_BASE_X + typeIndex * COLUMN_GAP,
        y: 40 + row * ROW_GAP,
      },
      data: {
        label: node.label,
        entity_type: entityType,
        entity_id: String(node.entity_id),
        color,
        properties: (node.properties as Record<string, unknown>) ?? {},
      },
    };
  });
}

export function knowledgeGraphEdgesToFlow(
  edges: KnowledgeGraphEdge[],
  visibleNodeIds: Set<string>,
): Edge[] {
  return edges
    .map((edge) => {
      const source = graphNodeKey(edge.source_type, edge.source_id);
      const target = graphNodeKey(edge.target_type, edge.target_id);
      if (!visibleNodeIds.has(source) || !visibleNodeIds.has(target)) {
        return null;
      }
      return {
        id: edge.id || `e-${source}-${target}-${edge.relation_type}`,
        source,
        target,
        type: "smoothstep",
        label: edge.relation_type,
        labelStyle: { fill: "rgba(255,255,255,0.55)", fontSize: 10 },
        style: { strokeWidth: 1.5, stroke: "rgba(255,255,255,0.25)" },
      } satisfies Edge;
    })
    .filter((edge): edge is Edge => edge !== null);
}

export function mergeNeighborNodes(
  current: KnowledgeGraphNode[],
  neighbors: KnowledgeGraphEdge[],
  detailLabel?: string,
  detailType?: string,
  detailId?: string,
): KnowledgeGraphNode[] {
  const map = new Map(
    current.map((node) => [
      graphNodeKey(String(node.entity_type), String(node.entity_id)),
      node,
    ]),
  );

  if (detailType && detailId && detailLabel) {
    const key = graphNodeKey(detailType, detailId);
    if (!map.has(key)) {
      map.set(key, {
        id: key,
        entity_type: detailType,
        entity_id: detailId,
        label: detailLabel,
        properties: {},
      });
    }
  }

  for (const edge of neighbors) {
    const targetKey = graphNodeKey(edge.target_type, edge.target_id);
    if (!map.has(targetKey)) {
      map.set(targetKey, {
        id: targetKey,
        entity_type: edge.target_type,
        entity_id: edge.target_id,
        label: edge.target_id,
        properties: {},
      });
    }
    const sourceKey = graphNodeKey(edge.source_type, edge.source_id);
    if (!map.has(sourceKey)) {
      map.set(sourceKey, {
        id: sourceKey,
        entity_type: edge.source_type,
        entity_id: edge.source_id,
        label: edge.source_id,
        properties: {},
      });
    }
  }

  return [...map.values()];
}
