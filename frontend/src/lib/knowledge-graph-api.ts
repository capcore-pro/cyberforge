import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";

const KG = `${API_PREFIX}/knowledge-graph`;

export type KnowledgeGraphEntityType =
  | "agent"
  | "project"
  | "client"
  | "document"
  | "workflow"
  | "tool"
  | "prompt"
  | "memory";

export interface KnowledgeGraphNode {
  id: string;
  entity_type: KnowledgeGraphEntityType | string;
  entity_id: string;
  label: string;
  properties: Record<string, unknown>;
  organization_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface KnowledgeGraphEdge {
  id: string;
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  relation_type: string;
  weight: number;
  properties?: Record<string, unknown>;
  created_at?: string;
}

export interface KnowledgeGraphStats {
  nodes: Record<string, number>;
  edges: Record<string, number>;
  total_nodes: number;
  total_edges: number;
}

export interface KnowledgeGraphSyncResult {
  nodes_created: number;
  edges_created: number;
  status: string;
}

export interface KnowledgeGraphTraverseRow {
  node_type: string;
  node_id: string;
  node_label: string;
  relation: string | null;
  depth: number;
  path: string;
}

export interface KnowledgeGraphNodeDetail extends KnowledgeGraphNode {
  neighbors: KnowledgeGraphEdge[];
}

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  agent: "#d4a843",
  workflow: "#6366f1",
  project: "#0ea5e9",
  client: "#10b981",
  document: "#f59e0b",
  tool: "#8b5cf6",
  prompt: "#06b6d4",
  memory: "#ec4899",
};

export const ENTITY_TYPE_LABELS: Record<string, string> = {
  agent: "Agent",
  workflow: "Workflow",
  project: "Projet",
  client: "Client",
  document: "Document",
  tool: "Outil",
  prompt: "Prompt",
  memory: "Mémoire",
};

export function graphNodeKey(
  entityType: string,
  entityId: string,
): string {
  return `${entityType}:${entityId}`;
}

export async function fetchKnowledgeGraphNodes(
  entityType?: string,
  limit = 200,
): Promise<KnowledgeGraphNode[]> {
  const q = new URLSearchParams();
  if (entityType?.trim()) q.set("entity_type", entityType.trim());
  q.set("limit", String(limit));
  const suffix = q.toString() ? `?${q}` : "";
  const res = await apiRequest<KnowledgeGraphNode[]>({
    method: "GET",
    path: `${KG}/nodes${suffix}`,
  });
  if (!res.ok) {
    throw new Error(
      apiErrorMessage(res, "Impossible de charger les nœuds du graphe."),
    );
  }
  return Array.isArray(res.data) ? res.data : [];
}

export async function fetchKnowledgeGraphEdges(
  limit = 500,
): Promise<KnowledgeGraphEdge[]> {
  const res = await apiRequest<KnowledgeGraphEdge[]>({
    method: "GET",
    path: `${KG}/edges?limit=${limit}`,
  });
  if (!res.ok) {
    throw new Error(
      apiErrorMessage(res, "Impossible de charger les arêtes du graphe."),
    );
  }
  return Array.isArray(res.data) ? res.data : [];
}

export async function fetchKnowledgeGraphStats(): Promise<KnowledgeGraphStats> {
  const res = await apiRequest<KnowledgeGraphStats>({
    method: "GET",
    path: `${KG}/stats`,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Statistiques graphe indisponibles."));
  }
  return res.data;
}

export async function syncKnowledgeGraph(): Promise<KnowledgeGraphSyncResult> {
  const res = await apiRequest<KnowledgeGraphSyncResult>({
    method: "POST",
    path: `${KG}/sync`,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Synchronisation du graphe impossible."));
  }
  return res.data;
}

export async function fetchKnowledgeGraphNodeDetail(
  entityType: string,
  entityId: string,
): Promise<KnowledgeGraphNodeDetail> {
  const res = await apiRequest<KnowledgeGraphNodeDetail>({
    method: "GET",
    path: `${KG}/nodes/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Nœud introuvable."));
  }
  return res.data;
}

export async function traverseKnowledgeGraph(
  entityType: string,
  entityId: string,
  maxDepth = 3,
): Promise<KnowledgeGraphTraverseRow[]> {
  const res = await apiRequest<KnowledgeGraphTraverseRow[]>({
    method: "GET",
    path: `${KG}/traverse/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}?max_depth=${maxDepth}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Traversal graphe impossible."));
  }
  return Array.isArray(res.data) ? res.data : [];
}
