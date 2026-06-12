-- CyberForge — LLM Provider Layer (registre providers + modèles)

CREATE TABLE IF NOT EXISTS llm_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  priority INTEGER DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO llm_providers (name, slug, priority) VALUES
  ('Anthropic', 'anthropic', 1),
  ('OpenAI', 'openai', 2),
  ('DeepSeek', 'deepseek', 3),
  ('Ollama', 'ollama', 4)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS llm_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL
    REFERENCES llm_providers(id),
  model_name VARCHAR(255) NOT NULL,
  model_slug VARCHAR(255) UNIQUE NOT NULL,
  context_window INTEGER DEFAULT 200000,
  input_cost_per_million DECIMAL(12,6) DEFAULT 0,
  output_cost_per_million DECIMAL(12,6) DEFAULT 0,
  capabilities JSONB DEFAULT '[]',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_models_provider
ON llm_models(provider_id);

CREATE INDEX IF NOT EXISTS idx_llm_models_slug
ON llm_models(model_slug);

INSERT INTO llm_models
  (provider_id, model_name, model_slug,
   context_window,
   input_cost_per_million, output_cost_per_million,
   capabilities)
SELECT
  p.id,
  m.model_name, m.model_slug,
  m.context_window,
  m.input_cost, m.output_cost,
  m.capabilities::jsonb
FROM llm_providers p
JOIN (VALUES
  ('claude-haiku-4-5-20251001',
   'claude-haiku-4-5',
   200000, 0.80, 4.00,
   '["chat","analysis","fast"]'),
  ('claude-sonnet-4-5',
   'claude-sonnet-4-5',
   200000, 3.00, 15.00,
   '["chat","reasoning","coding","generation"]'),
  ('claude-opus-4-6',
   'claude-opus-4-6',
   200000, 15.00, 75.00,
   '["chat","reasoning","coding","architecture"]')
) AS m(model_name, model_slug,
       context_window, input_cost, output_cost,
       capabilities)
ON (p.slug = 'anthropic')
ON CONFLICT (model_slug) DO NOTHING;

INSERT INTO llm_models
  (provider_id, model_name, model_slug,
   context_window,
   input_cost_per_million, output_cost_per_million,
   capabilities)
SELECT
  p.id,
  m.model_name, m.model_slug,
  m.context_window,
  m.input_cost, m.output_cost,
  m.capabilities::jsonb
FROM llm_providers p
JOIN (VALUES
  ('gpt-4o', 'gpt-4o',
   128000, 2.50, 10.00,
   '["chat","reasoning","coding","vision"]'),
  ('gpt-4o-mini', 'gpt-4o-mini',
   128000, 0.15, 0.60,
   '["chat","analysis","fast"]')
) AS m(model_name, model_slug,
       context_window, input_cost, output_cost,
       capabilities)
ON (p.slug = 'openai')
ON CONFLICT (model_slug) DO NOTHING;

INSERT INTO llm_models
  (provider_id, model_name, model_slug,
   context_window,
   input_cost_per_million, output_cost_per_million,
   capabilities)
SELECT
  p.id,
  m.model_name, m.model_slug,
  m.context_window,
  m.input_cost, m.output_cost,
  m.capabilities::jsonb
FROM llm_providers p
JOIN (VALUES
  ('deepseek-chat', 'deepseek-chat',
   64000, 0.14, 0.28,
   '["chat","analysis","fast","economical"]')
) AS m(model_name, model_slug,
       context_window, input_cost, output_cost,
       capabilities)
ON (p.slug = 'deepseek')
ON CONFLICT (model_slug) DO NOTHING;

ALTER TABLE llm_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_models ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_llm_providers"
  ON llm_providers FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_llm_models"
  ON llm_models FOR ALL TO service_role
  USING (true) WITH CHECK (true);
