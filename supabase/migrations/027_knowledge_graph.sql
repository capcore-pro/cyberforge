-- CyberForge — Knowledge Graph (nœuds, arêtes, traversal récursif)

CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(100) NOT NULL,
  entity_id VARCHAR(255) NOT NULL,
  label VARCHAR(255) NOT NULL,
  properties JSONB DEFAULT '{}',
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_type
ON knowledge_graph_nodes(entity_type);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_entity
ON knowledge_graph_nodes(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type VARCHAR(100) NOT NULL,
  source_id VARCHAR(255) NOT NULL,
  target_type VARCHAR(100) NOT NULL,
  target_id VARCHAR(255) NOT NULL,
  relation_type VARCHAR(100) NOT NULL,
  weight FLOAT DEFAULT 1.0,
  properties JSONB DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(source_type, source_id,
         target_type, target_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source
ON knowledge_graph_edges(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_target
ON knowledge_graph_edges(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_relation
ON knowledge_graph_edges(relation_type);

CREATE OR REPLACE FUNCTION traverse_knowledge_graph(
  start_entity_type VARCHAR,
  start_entity_id VARCHAR,
  max_depth INT DEFAULT 3
)
RETURNS TABLE (
  node_type VARCHAR,
  node_id VARCHAR,
  node_label VARCHAR,
  relation VARCHAR,
  depth INT,
  path TEXT
)
LANGUAGE sql STABLE AS $$
  WITH RECURSIVE graph_traversal AS (
    SELECT
      n.entity_type AS node_type,
      n.entity_id AS node_id,
      n.label AS node_label,
      NULL::VARCHAR AS relation,
      0 AS depth,
      n.entity_type || ':' || n.entity_id AS path
    FROM knowledge_graph_nodes n
    WHERE n.entity_type = start_entity_type
      AND n.entity_id = start_entity_id

    UNION ALL

    SELECT
      target_n.entity_type,
      target_n.entity_id,
      target_n.label,
      e.relation_type,
      gt.depth + 1,
      gt.path || ' → ' || e.relation_type
        || ' → ' || target_n.entity_type
        || ':' || target_n.entity_id
    FROM graph_traversal gt
    JOIN knowledge_graph_edges e
      ON e.source_type = gt.node_type
      AND e.source_id = gt.node_id
    JOIN knowledge_graph_nodes target_n
      ON target_n.entity_type = e.target_type
      AND target_n.entity_id = e.target_id
    WHERE gt.depth < max_depth
      AND gt.path NOT LIKE
        '%' || target_n.entity_id || '%'
  )
  SELECT * FROM graph_traversal
  ORDER BY depth, node_type;
$$;
