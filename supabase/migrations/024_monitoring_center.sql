-- CyberForge — Monitoring Center Volume 05G
-- Sources, alertes et incidents

CREATE TABLE IF NOT EXISTS monitoring_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name VARCHAR(255) NOT NULL UNIQUE,
  source_type VARCHAR(100) NOT NULL,
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO monitoring_sources
  (source_name, source_type) VALUES
  ('llm_usage', 'cost'),
  ('agent_executions', 'agents'),
  ('supervisor_decisions', 'quality'),
  ('workflow_executions', 'workflows'),
  ('tool_executions', 'tools'),
  ('audit_logs', 'audit'),
  ('api_health', 'infrastructure')
ON CONFLICT (source_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  alert_type VARCHAR(100) NOT NULL,
  severity VARCHAR(50) NOT NULL
    DEFAULT 'warning',
  title VARCHAR(255) NOT NULL,
  message TEXT,
  source VARCHAR(100),
  source_id VARCHAR(255),
  status VARCHAR(50) DEFAULT 'open',
  acknowledged_at TIMESTAMP,
  resolved_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_status
ON alerts(status);

CREATE INDEX IF NOT EXISTS idx_alerts_severity
ON alerts(severity);

CREATE INDEX IF NOT EXISTS idx_alerts_created
ON alerts(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_type_open
ON alerts(alert_type, status);

CREATE TABLE IF NOT EXISTS incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  title VARCHAR(255) NOT NULL,
  description TEXT,
  severity VARCHAR(50) NOT NULL
    DEFAULT 'medium',
  status VARCHAR(50) DEFAULT 'open',
  source VARCHAR(100),
  alert_id UUID REFERENCES alerts(id),
  detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMP,
  resolution_notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_status
ON incidents(status);

CREATE INDEX IF NOT EXISTS idx_incidents_severity
ON incidents(severity);

CREATE INDEX IF NOT EXISTS idx_incidents_created
ON incidents(created_at DESC);
