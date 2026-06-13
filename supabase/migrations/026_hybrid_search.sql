-- CyberForge — Knowledge Engine hybrid search (vector + keyword)

CREATE OR REPLACE FUNCTION search_knowledge_hybrid(
  query_embedding VECTOR(1536),
  query_text TEXT,
  match_project_id UUID DEFAULT NULL,
  match_org_id UUID
    DEFAULT '00000000-0000-0000-0000-000000000001',
  match_count INT DEFAULT 10,
  vector_weight FLOAT DEFAULT 0.7,
  keyword_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  document_title VARCHAR,
  content TEXT,
  similarity FLOAT,
  keyword_score FLOAT,
  combined_score FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    ke.chunk_id,
    ke.document_id,
    kd.title AS document_title,
    kc.content,
    1 - (ke.embedding <=> query_embedding)
      AS similarity,
    ts_rank(
      to_tsvector('french', kc.content),
      plainto_tsquery('french', query_text)
    ) AS keyword_score,
    (
      vector_weight *
        (1 - (ke.embedding <=> query_embedding))
      + keyword_weight * ts_rank(
          to_tsvector('french', kc.content),
          plainto_tsquery('french', query_text)
        )
    ) AS combined_score
  FROM knowledge_embeddings ke
  JOIN knowledge_chunks kc ON kc.id = ke.chunk_id
  JOIN knowledge_documents kd
    ON kd.id = ke.document_id
  WHERE
    (match_project_id IS NULL
      OR ke.project_id = match_project_id)
    AND ke.organization_id = match_org_id
    AND kd.deleted_at IS NULL
  ORDER BY combined_score DESC
  LIMIT match_count;
$$;
