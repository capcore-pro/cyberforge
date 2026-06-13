-- CyberForge — Security events (Volume 7)

CREATE TABLE IF NOT EXISTS security_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  event_type VARCHAR(100) NOT NULL,
  severity VARCHAR(50) NOT NULL
    DEFAULT 'low',
  source VARCHAR(255),
  actor_type VARCHAR(100),
  actor_id VARCHAR(255),
  description TEXT,
  metadata JSONB DEFAULT '{}',
  resolved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sec_events_type
ON security_events(event_type);

CREATE INDEX IF NOT EXISTS idx_sec_events_severity
ON security_events(severity);

CREATE INDEX IF NOT EXISTS idx_sec_events_created
ON security_events(created_at DESC);

-- Types d'événements CyberForge
-- api_key_changed : clé API modifiée
-- api_key_missing : clé requise absente
-- agent_disabled : agent désactivé
-- agent_model_changed : modèle agent changé
-- vault_accessed : coffre de secrets ouvert
-- generation_failed_repeatedly : échecs répétés
-- high_cost_detected : coût anormal détecté
