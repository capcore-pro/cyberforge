-- CyberForge — Supervisor System Volume 04B
-- Décisions, quality reviews, métriques agrégées

CREATE TABLE IF NOT EXISTS supervisor_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generation_id VARCHAR(255),
  project_id UUID,
  decision_type VARCHAR(100) NOT NULL,
  agent_validated VARCHAR(100),
  valid BOOLEAN NOT NULL,
  quality_score INTEGER DEFAULT 0,
  errors JSONB DEFAULT '[]',
  warnings JSONB DEFAULT '[]',
  attempt_number INTEGER DEFAULT 1,
  duration_ms BIGINT DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sup_decisions_gen
ON supervisor_decisions(generation_id);

CREATE INDEX IF NOT EXISTS idx_sup_decisions_type
ON supervisor_decisions(decision_type);

CREATE INDEX IF NOT EXISTS idx_sup_decisions_valid
ON supervisor_decisions(valid);

CREATE TABLE IF NOT EXISTS quality_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generation_id VARCHAR(255),
  project_id UUID,
  review_type VARCHAR(100) NOT NULL,
  score INTEGER NOT NULL,
  max_score INTEGER DEFAULT 100,
  passed BOOLEAN NOT NULL,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_gen
ON quality_reviews(generation_id);

CREATE TABLE IF NOT EXISTS supervisor_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_date DATE NOT NULL,
  total_validations INTEGER DEFAULT 0,
  passed_first_try INTEGER DEFAULT 0,
  total_retries INTEGER DEFAULT 0,
  avg_quality_score DECIMAL(5,2) DEFAULT 0,
  avg_attempts DECIMAL(5,2) DEFAULT 0,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sup_metrics_date
ON supervisor_metrics(period_date);
