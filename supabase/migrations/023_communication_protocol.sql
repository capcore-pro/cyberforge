-- CyberForge — Agent Communication Protocol Volume 04G

CREATE TABLE IF NOT EXISTS communication_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_name VARCHAR(255) UNIQUE NOT NULL,
  channel_type VARCHAR(100) NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO communication_channels
  (channel_name, channel_type, description)
VALUES
  ('supervisor_corrections',
   'direct',
   'SupervisorAI → agents : corrections et retries'),
  ('schema_propagation',
   'broadcast',
   'DatabaseAI → AuthAI/PaymentAI : schéma produit'),
  ('context_enrichment',
   'broadcast',
   'Knowledge/Memory → GeneratorAI : contexte enrichi'),
  ('pipeline_events',
   'broadcast',
   'Pipeline → tous : événements de progression')
ON CONFLICT (channel_name) DO NOTHING;

ALTER TABLE agent_messages
ADD COLUMN IF NOT EXISTS channel_name
  VARCHAR(255) DEFAULT 'pipeline_events';

ALTER TABLE agent_messages
ADD COLUMN IF NOT EXISTS priority
  VARCHAR(50) DEFAULT 'normal';

CREATE TABLE IF NOT EXISTS message_acks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL
    REFERENCES agent_messages(id)
    ON DELETE CASCADE,
  agent_id VARCHAR(100) NOT NULL,
  status VARCHAR(50) DEFAULT 'received',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acks_message
ON message_acks(message_id);

CREATE TABLE IF NOT EXISTS communication_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_date DATE NOT NULL,
  channel_name VARCHAR(255),
  messages_sent INTEGER DEFAULT 0,
  messages_acked INTEGER DEFAULT 0,
  avg_latency_ms DECIMAL(10,2) DEFAULT 0,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_comm_analytics_period
ON communication_analytics(period_date, channel_name);
