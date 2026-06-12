-- CyberForge — LLM usage + cost tracking (pipeline V2)
-- Exécuter dans l'éditeur SQL Supabase ou via supabase db push

-- Table llm_usage
CREATE TABLE IF NOT EXISTS llm_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  generation_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  agent_name VARCHAR(100) NOT NULL,
  provider VARCHAR(100) NOT NULL,
  model VARCHAR(255) NOT NULL,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  cost_usd DECIMAL(12,6) DEFAULT 0,
  duration_ms BIGINT DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_project
ON llm_usage(project_id);

CREATE INDEX IF NOT EXISTS idx_llm_usage_agent
ON llm_usage(agent_name);

CREATE INDEX IF NOT EXISTS idx_llm_usage_created
ON llm_usage(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_usage_generation
ON llm_usage(generation_id);

-- Table cost_tracking (agrégats journaliers)
CREATE TABLE IF NOT EXISTS cost_tracking (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  period VARCHAR(20) NOT NULL,
  period_date DATE NOT NULL,
  total_cost_usd DECIMAL(12,6) DEFAULT 0,
  total_tokens BIGINT DEFAULT 0,
  generations_count INTEGER DEFAULT 0,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_period
ON cost_tracking(organization_id, period, period_date);

-- Mettre à jour colonnes generations existantes
ALTER TABLE generations
ALTER COLUMN duration_ms SET DEFAULT 0,
ALTER COLUMN estimated_cost_usd SET DEFAULT 0;

-- Ajouter colonnes tokens à generations
ALTER TABLE generations
ADD COLUMN IF NOT EXISTS input_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS output_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_tokens INTEGER DEFAULT 0;

ALTER TABLE llm_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_llm_usage"
  ON llm_usage
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "service_role_all_cost_tracking"
  ON cost_tracking
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
