-- CyberForge — Knowledge Engine (pgvector, RAG)
-- Exécuter dans l'éditeur SQL Supabase ou via supabase db push

-- 1. Extension pgvector (déjà activée manuellement)
CREATE EXTENSION IF NOT EXISTS vector
SCHEMA public;

-- 2. Table organizations (prérequis V3)
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  owner_id UUID,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP NULL
);

-- Seed : organisation CapCore par défaut
INSERT INTO organizations (id, name, slug)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'CapCore',
  'capcore'
) ON CONFLICT (slug) DO NOTHING;

-- 3. Table workspaces
CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    REFERENCES organizations(id),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP NULL
);

-- Seed : workspace Default
INSERT INTO workspaces (id, organization_id, name, slug)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',
  'Default',
  'default'
) ON CONFLICT (slug) DO NOTHING;

-- 4. Enrichir projects avec organization_id + workspace_id
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS organization_id UUID
  DEFAULT '00000000-0000-0000-0000-000000000001';

ALTER TABLE projects
ADD COLUMN IF NOT EXISTS workspace_id UUID
  DEFAULT '00000000-0000-0000-0000-000000000002';

-- 5. Table knowledge_documents
CREATE TABLE IF NOT EXISTS knowledge_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  title VARCHAR(255) NOT NULL,
  source_type VARCHAR(100) NOT NULL
    DEFAULT 'manual',
  language VARCHAR(20) DEFAULT 'fr',
  file_path TEXT,
  content TEXT,
  content_hash VARCHAR(255),
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_project
ON knowledge_documents(project_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_org
ON knowledge_documents(organization_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status
ON knowledge_documents(status);

-- 6. Table knowledge_chunks
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL
    REFERENCES knowledge_documents(id)
    ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  token_count INTEGER,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document
ON knowledge_chunks(document_id);

-- 7. Table knowledge_embeddings (pgvector)
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID NOT NULL
    REFERENCES knowledge_chunks(id)
    ON DELETE CASCADE,
  document_id UUID NOT NULL,
  project_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  embedding_model VARCHAR(255)
    DEFAULT 'text-embedding-3-small',
  embedding VECTOR(1536),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk
ON knowledge_embeddings(chunk_id);

CREATE INDEX IF NOT EXISTS idx_embeddings_project
ON knowledge_embeddings(project_id);

-- Index cosine similarity pour la recherche RAG
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON knowledge_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 8. Fonction de recherche RAG
CREATE OR REPLACE FUNCTION search_knowledge(
  query_embedding VECTOR(1536),
  match_project_id UUID DEFAULT NULL,
  match_org_id UUID DEFAULT '00000000-0000-0000-0000-000000000001',
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  document_title VARCHAR,
  content TEXT,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    ke.chunk_id,
    ke.document_id,
    kd.title AS document_title,
    kc.content,
    1 - (ke.embedding <=> query_embedding) AS similarity
  FROM knowledge_embeddings ke
  JOIN knowledge_chunks kc ON kc.id = ke.chunk_id
  JOIN knowledge_documents kd ON kd.id = ke.document_id
  WHERE
    (match_project_id IS NULL
      OR ke.project_id = match_project_id)
    AND ke.organization_id = match_org_id
    AND kd.deleted_at IS NULL
  ORDER BY ke.embedding <=> query_embedding
  LIMIT match_count;
$$;
