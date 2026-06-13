-- CyberForge — Historique des déploiements (Volume 06A)

CREATE TABLE IF NOT EXISTS deployments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  generation_id VARCHAR(255),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  deployment_name VARCHAR(255),
  deployment_type VARCHAR(100)
    DEFAULT 'application',
  provider VARCHAR(100) DEFAULT 'cloudflare',
  environment VARCHAR(50) DEFAULT 'production',
  status VARCHAR(50) DEFAULT 'pending',
  url TEXT,
  duration_ms BIGINT DEFAULT 0,
  error_message TEXT,
  deployed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployments_project
ON deployments(project_id);

CREATE INDEX IF NOT EXISTS idx_deployments_status
ON deployments(status);

CREATE INDEX IF NOT EXISTS idx_deployments_created
ON deployments(created_at DESC);
