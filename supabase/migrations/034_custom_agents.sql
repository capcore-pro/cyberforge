-- CyberForge — Custom Agents (Agent Builder UI)
-- Table custom_agents utilisée par /api/agents/custom

CREATE TABLE IF NOT EXISTS public.custom_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  system_prompt TEXT NOT NULL,
  model VARCHAR(255) NOT NULL,
  temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
  max_tokens INTEGER NOT NULL DEFAULT 2048,
  tools JSONB NOT NULL DEFAULT '[]',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custom_agents_active
ON public.custom_agents (is_active);

CREATE INDEX IF NOT EXISTS idx_custom_agents_updated
ON public.custom_agents (updated_at DESC);

ALTER TABLE public.custom_agents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_custom_agents" ON public.custom_agents;
CREATE POLICY "service_role_all_custom_agents"
  ON public.custom_agents
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

