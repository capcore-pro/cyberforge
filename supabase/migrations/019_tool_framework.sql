-- CyberForge — Tool Framework (registre, exécutions, audit)
-- 8 outils pipeline V2 seedés

CREATE TABLE IF NOT EXISTS tool_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  category VARCHAR(100) NOT NULL,
  description TEXT,
  version VARCHAR(50) DEFAULT '1.0.0',
  requires_key VARCHAR(100),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id VARCHAR(100) NOT NULL,
  agent_id VARCHAR(100),
  project_id UUID,
  generation_id UUID,
  action VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  duration_ms BIGINT DEFAULT 0,
  error_message TEXT,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_exec_tool
ON tool_executions(tool_id);

CREATE INDEX IF NOT EXISTS idx_tool_exec_project
ON tool_executions(project_id);

CREATE INDEX IF NOT EXISTS idx_tool_exec_status
ON tool_executions(status);

CREATE INDEX IF NOT EXISTS idx_tool_exec_created
ON tool_executions(created_at DESC);

CREATE TABLE IF NOT EXISTS tool_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id VARCHAR(100) NOT NULL,
  agent_id VARCHAR(100),
  action VARCHAR(255) NOT NULL,
  result VARCHAR(100),
  metadata JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_audit_tool
ON tool_audit_logs(tool_id);

INSERT INTO tool_registry (
  tool_id, name, slug, category,
  description, requires_key
) VALUES
(
  'pexels', 'Pexels', 'pexels',
  'media',
  'Recherche et injection de photos haute résolution',
  'pexels'
),
(
  'cloudflare_pages', 'Cloudflare Pages',
  'cloudflare-pages', 'deployment',
  'Déploiement de sites statiques sur Cloudflare Pages',
  'cloudflare'
),
(
  'firecrawl', 'Firecrawl', 'firecrawl',
  'scraping',
  'Scrape et analyse de sites web pour inspiration et clone',
  'firecrawl'
),
(
  'brevo', 'Brevo', 'brevo',
  'communication',
  'Envoi d emails transactionnels via API Brevo',
  'brevo'
),
(
  'replicate', 'Replicate', 'replicate',
  'media',
  'Génération et upscaling d images via Replicate API',
  'replicate'
),
(
  'anthropic_api', 'Anthropic API',
  'anthropic-api', 'llm',
  'Appels API Anthropic Claude pour les agents LLM',
  'anthropic'
),
(
  'openai_api', 'OpenAI API',
  'openai-api', 'llm',
  'Appels API OpenAI GPT pour les fallbacks LLM',
  'openai'
),
(
  'stripe_js', 'Stripe JS', 'stripe-js',
  'payment',
  'Injection du script Stripe Checkout dans les sites e-commerce',
  null
)
ON CONFLICT (tool_id) DO UPDATE SET
  name = EXCLUDED.name,
  updated_at = NOW();
