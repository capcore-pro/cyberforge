import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GHOST_BTN, TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import { KnowledgeGraphNode as KnowledgeGraphNodeComponent } from "@/components/knowledge/KnowledgeGraphNode";
import { Button } from "@/components/ui";
import {
  ENTITY_TYPE_COLORS,
  ENTITY_TYPE_LABELS,
  fetchKnowledgeGraphEdges,
  fetchKnowledgeGraphNodeDetail,
  fetchKnowledgeGraphNodes,
  fetchKnowledgeGraphStats,
  graphNodeKey,
  syncKnowledgeGraph,
  type KnowledgeGraphEdge,
  type KnowledgeGraphNode,
  type KnowledgeGraphStats,
} from "@/lib/knowledge-graph-api";
import {
  knowledgeGraphEdgesToFlow,
  layoutKnowledgeGraphNodes,
  mergeNeighborNodes,
  type KnowledgeGraphNodeData,
} from "@/lib/knowledge-graph-layout";

const nodeTypes = { knowledgeGraphNode: KnowledgeGraphNodeComponent };

const FILTER_TYPES = [
  "agent",
  "workflow",
  "project",
  "client",
  "document",
  "tool",
  "prompt",
  "memory",
] as const;

export function KnowledgeGraphView() {
  const [nodes, setNodes] = useState<KnowledgeGraphNode[]>([]);
  const [edges, setEdges] = useState<KnowledgeGraphEdge[]>([]);
  const [stats, setStats] = useState<KnowledgeGraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [selected, setSelected] = useState<Node<KnowledgeGraphNodeData> | null>(
    null,
  );
  const [panelBusy, setPanelBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nodeRows, edgeRows, statRows] = await Promise.all([
        fetchKnowledgeGraphNodes(undefined, 300),
        fetchKnowledgeGraphEdges(1000),
        fetchKnowledgeGraphStats(),
      ]);
      setNodes(nodeRows);
      setEdges(edgeRows);
      setStats(statRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setNodes([]);
      setEdges([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredNodes = useMemo(() => {
    if (!typeFilter) return nodes;
    return nodes.filter((node) => node.entity_type === typeFilter);
  }, [nodes, typeFilter]);

  const flowNodes = useMemo(
    () => layoutKnowledgeGraphNodes(filteredNodes),
    [filteredNodes],
  );

  const visibleIds = useMemo(
    () => new Set(flowNodes.map((node) => node.id)),
    [flowNodes],
  );

  const flowEdges = useMemo(
    () => knowledgeGraphEdgesToFlow(edges, visibleIds),
    [edges, visibleIds],
  );

  async function handleSync() {
    setSyncing(true);
    setError(null);
    try {
      await syncKnowledgeGraph();
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Synchronisation impossible.",
      );
    } finally {
      setSyncing(false);
    }
  }

  async function handleShowNeighbors() {
    if (!selected) return;
    const data = selected.data;
    setPanelBusy(true);
    setError(null);
    try {
      const detail = await fetchKnowledgeGraphNodeDetail(
        data.entity_type,
        data.entity_id,
      );
      const merged = mergeNeighborNodes(
        nodes,
        detail.neighbors,
        detail.label,
        detail.entity_type,
        detail.entity_id,
      );
      setNodes(merged);
      const edgeRows = await fetchKnowledgeGraphEdges(1000);
      setEdges(edgeRows);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Voisins indisponibles.",
      );
    } finally {
      setPanelBusy(false);
    }
  }

  const isEmpty = !loading && nodes.length === 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setTypeFilter(null)}
            className={`${TAB_BASE} rounded-control ${typeFilter === null ? TAB_ACTIVE : ""}`}
          >
            Tout afficher
          </button>
          {FILTER_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setTypeFilter(type)}
              className={`${TAB_BASE} rounded-control ${typeFilter === type ? TAB_ACTIVE : ""}`}
            >
              {ENTITY_TYPE_LABELS[type] ?? type}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {stats ? (
            <span className="text-xs text-white/40">
              {stats.total_nodes} nœuds · {stats.total_edges} arêtes
            </span>
          ) : null}
          <Button variant="primary" loading={syncing} onClick={() => void handleSync()}>
            Synchroniser
          </Button>
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="relative min-h-[420px] overflow-hidden rounded-card border border-white/10 bg-white/[0.02]">
          {loading ? (
            <p className="flex h-[420px] items-center justify-center text-sm text-white/50">
              Chargement du graphe…
            </p>
          ) : isEmpty ? (
            <div className="flex h-[420px] flex-col items-center justify-center gap-4 px-6 text-center">
              <i className="ti ti-git-fork text-4xl text-white/20" aria-hidden />
              <p className="max-w-md text-sm text-white/50">
                Graphe vide — cliquez sur Synchroniser pour construire le graphe
                depuis les données existantes.
              </p>
              <Button variant="primary" loading={syncing} onClick={() => void handleSync()}>
                Synchroniser
              </Button>
            </div>
          ) : (
            <div className="h-[min(70vh,520px)] w-full">
              <ReactFlowProvider>
                <ReactFlow
                  nodes={flowNodes}
                  edges={flowEdges}
                  nodeTypes={nodeTypes}
                  fitView
                  fitViewOptions={{ padding: 0.25 }}
                  proOptions={{ hideAttribution: true }}
                  onNodeClick={(_, node) =>
                    setSelected(node as Node<KnowledgeGraphNodeData>)
                  }
                  panOnDrag
                  zoomOnScroll
                  nodesDraggable
                  nodesConnectable={false}
                >
                  <Background color="rgba(255,255,255,0.03)" gap={24} />
                  <Controls
                    style={{
                      background: "var(--cf-bg-card)",
                      border: "1px solid var(--cf-border)",
                    }}
                  />
                  <MiniMap
                    nodeColor={(node) =>
                      String(
                        (node.data as KnowledgeGraphNodeData)?.color ?? "#888",
                      )
                    }
                    style={{ background: "var(--cf-bg-secondary)" }}
                  />
                </ReactFlow>
              </ReactFlowProvider>
            </div>
          )}
        </div>

        <aside className="rounded-card border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl">
          {selected ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-white/40">
                  Nœud sélectionné
                </p>
                <h3 className="mt-1 text-sm font-semibold text-white">
                  {selected.data.label}
                </h3>
                <div className="mt-2">
                  <span
                    className="inline-flex rounded-full border px-2 py-0.5 text-xs font-medium"
                    style={{
                      borderColor: `${selected.data.color}55`,
                      color: selected.data.color,
                      backgroundColor: `${selected.data.color}15`,
                    }}
                  >
                    {selected.data.entity_type}
                  </span>
                </div>
                <p className="mt-2 font-mono text-[11px] text-white/40">
                  {graphNodeKey(
                    selected.data.entity_type,
                    selected.data.entity_id,
                  )}
                </p>
              </div>

              <div>
                <p className="mb-2 text-xs uppercase tracking-widest text-white/40">
                  Propriétés
                </p>
                <pre className="max-h-48 overflow-auto rounded-control border border-white/10 bg-black/20 p-2 text-[11px] text-white/70">
                  {JSON.stringify(selected.data.properties ?? {}, null, 2)}
                </pre>
              </div>

              <Button
                variant="ghost"
                loading={panelBusy}
                onClick={() => void handleShowNeighbors()}
              >
                Voir les voisins
              </Button>
            </div>
          ) : (
            <p className="text-sm text-white/40">
              Cliquez sur un nœud pour afficher ses détails.
            </p>
          )}
        </aside>
      </div>

      {stats && !isEmpty ? (
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.nodes).map(([type, count]) => (
            <span
              key={type}
              className="rounded-full border px-2 py-0.5 text-xs"
              style={{
                borderColor: `${ENTITY_TYPE_COLORS[type] ?? "#888"}55`,
                color: ENTITY_TYPE_COLORS[type] ?? "#aaa",
              }}
            >
              {ENTITY_TYPE_LABELS[type] ?? type}: {count}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
