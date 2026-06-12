-- CyberForge — Memory Engine (mémoire persistante + pgvector)
-- Exécuter dans l'éditeur SQL Supabase ou via supabase db push

-- 1. Table memory_entries
CREATE TABLE IF NOT EXISTS memory_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  agent_id VARCHAR(100),
  memory_type VARCHAR(100) NOT NULL,
  category VARCHAR(100) DEFAULT 'general',
  title VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  importance_score INTEGER DEFAULT 50,
  relevance_score INTEGER DEFAULT 50,
  access_count INTEGER DEFAULT 0,
  last_accessed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_project
ON memory_entries(project_id);

CREATE INDEX IF NOT EXISTS idx_memory_type
ON memory_entries(memory_type);

CREATE INDEX IF NOT EXISTS idx_memory_importance
ON memory_entries(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_memory_org
ON memory_entries(organization_id);

-- 2. Table memory_embeddings
CREATE TABLE IF NOT EXISTS memory_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_entry_id UUID NOT NULL
    REFERENCES memory_entries(id)
    ON DELETE CASCADE,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  project_id UUID,
  embedding_model VARCHAR(255)
    DEFAULT 'text-embedding-3-small',
  embedding VECTOR(1536),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mem_emb_entry
ON memory_embeddings(memory_entry_id);

CREATE INDEX IF NOT EXISTS idx_mem_emb_vector
ON memory_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 3. Fonction de recherche mémoire
CREATE OR REPLACE FUNCTION search_memories(
  query_embedding VECTOR(1536),
  match_project_id UUID DEFAULT NULL,
  match_org_id UUID
    DEFAULT '00000000-0000-0000-0000-000000000001',
  match_count INT DEFAULT 10,
  min_importance INT DEFAULT 0
)
RETURNS TABLE (
  memory_id UUID,
  title VARCHAR,
  content TEXT,
  memory_type VARCHAR,
  category VARCHAR,
  importance_score INTEGER,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    me.id AS memory_id,
    me.title,
    me.content,
    me.memory_type,
    me.category,
    me.importance_score,
    1 - (emb.embedding <=> query_embedding)
      AS similarity
  FROM memory_embeddings emb
  JOIN memory_entries me ON me.id = emb.memory_entry_id
  WHERE
    (match_project_id IS NULL
      OR me.project_id = match_project_id)
    AND me.organization_id = match_org_id
    AND me.importance_score >= min_importance
    AND me.deleted_at IS NULL
  ORDER BY emb.embedding <=> query_embedding
  LIMIT match_count;
$$;
