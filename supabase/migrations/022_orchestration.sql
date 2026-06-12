-- CyberForge — Multi-Agent Orchestration Volume 04C

CREATE TABLE IF NOT EXISTS agent_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generation_id VARCHAR(255) UNIQUE,
  project_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  workflow_id VARCHAR(100),
  status VARCHAR(50) DEFAULT 'created',
  agents_planned JSONB DEFAULT '[]',
  agents_completed JSONB DEFAULT '[]',
  agents_failed JSONB DEFAULT '[]',
  parallel_groups JSONB DEFAULT '[]',
  total_agents INTEGER DEFAULT 0,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_gen
ON agent_sessions(generation_id);

CREATE INDEX IF NOT EXISTS idx_sessions_project
ON agent_sessions(project_id);

CREATE TABLE IF NOT EXISTS shared_contexts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL
    REFERENCES agent_sessions(id)
    ON DELETE CASCADE,
  context_key VARCHAR(255) NOT NULL,
  context_value JSONB,
  produced_by VARCHAR(100),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_ctx_key
ON shared_contexts(session_id, context_key);

CREATE TABLE IF NOT EXISTS agent_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL
    REFERENCES agent_sessions(id)
    ON DELETE CASCADE,
  sender_agent VARCHAR(100) NOT NULL,
  receiver_agent VARCHAR(100),
  message_type VARCHAR(100) NOT NULL,
  payload JSONB DEFAULT '{}',
  status VARCHAR(50) DEFAULT 'sent',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_msg_session
ON agent_messages(session_id);

CREATE INDEX IF NOT EXISTS idx_agent_msg_receiver
ON agent_messages(receiver_agent);
