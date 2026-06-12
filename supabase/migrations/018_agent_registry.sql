-- CyberForge — Agent Registry (registre officiel des agents IA)
-- Table agents + agent_capabilities + seed 11 agents V2

CREATE TABLE IF NOT EXISTS agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  category VARCHAR(100) NOT NULL,
  description TEXT,
  version VARCHAR(50) DEFAULT '1.0.0',
  provider VARCHAR(100),
  model VARCHAR(255),
  capabilities JSONB DEFAULT '[]',
  system_prompt_slug VARCHAR(255),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  in_pipeline BOOLEAN NOT NULL DEFAULT FALSE,
  requires_key VARCHAR(100),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_category
ON agents(category);

CREATE INDEX IF NOT EXISTS idx_agents_slug
ON agents(slug);

CREATE INDEX IF NOT EXISTS idx_agents_enabled
ON agents(enabled);

CREATE TABLE IF NOT EXISTS agent_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID NOT NULL
    REFERENCES agents(id) ON DELETE CASCADE,
  capability_name VARCHAR(255) NOT NULL,
  capability_description TEXT
);

INSERT INTO agents (
  agent_id, name, slug, category,
  description, version, provider, model,
  capabilities, system_prompt_slug,
  in_pipeline, requires_key
) VALUES
(
  'brief', 'BriefAI', 'brief-ai',
  'ingestion',
  'Enrichit le brief client en 17 champs structurés',
  '2.0.0', 'anthropic', 'claude-haiku-4-5-20251001',
  '["brief_analysis","sector_detection","color_extraction"]',
  'brief-ai-system', true, 'anthropic'
),
(
  'design_system', 'DesignSystemAI',
  'design-system-ai', 'design',
  'Génère les tokens CSS cohérents selon le type de projet',
  '1.0.0', null, null,
  '["css_tokens","color_palette","typography"]',
  null, true, null
),
(
  'supervisor', 'SupervisorAI',
  'supervisor-ai', 'supervision',
  'Valide chaque étape du pipeline sans LLM',
  '2.0.0', null, null,
  '["brief_validation","html_validation","deployment_validation"]',
  'supervisor-validation-rules', true, null
),
(
  'generator', 'GeneratorAI',
  'generator-ai', 'generation',
  'Génère le HTML complet en un seul appel LLM',
  '2.0.0', 'anthropic', 'claude-sonnet-4-5',
  '["html_generation","multipage","ecommerce","crm","webapp"]',
  'generator-ai-system', true, 'anthropic'
),
(
  'deploy', 'DeployAI', 'deploy-ai',
  'deployment',
  'Injecte les assets et déploie sur Cloudflare Pages',
  '2.0.0', null, null,
  '["pexels_injection","stripe_injection","cart_injection","cloudflare_deploy"]',
  null, true, 'cloudflare'
),
(
  'database', 'DatabaseAI', 'database-ai',
  'database',
  'Génère le schéma SQL Supabase adapté au projet',
  '1.0.0', 'anthropic', 'claude-sonnet-4-5',
  '["sql_schema","rls_policies","migrations"]',
  null, true, 'supabase'
),
(
  'auth', 'AuthAI', 'auth-ai',
  'security',
  'Configure l authentification et les rôles Supabase',
  '1.0.0', 'anthropic', 'claude-sonnet-4-5',
  '["supabase_auth","rbac","rls"]',
  null, true, 'supabase'
),
(
  'payment', 'PaymentAI', 'payment-ai',
  'payment',
  'Configure Stripe et génère la config paiement',
  '1.0.0', 'anthropic', 'claude-sonnet-4-5',
  '["stripe_config","checkout","webhooks"]',
  null, true, 'stripe'
),
(
  'email', 'EmailAI', 'email-ai',
  'communication',
  'Envoie les notifications transactionnelles via Brevo',
  '1.0.0', null, null,
  '["deployment_notification","order_confirmation","reservation_confirmation"]',
  null, false, 'brevo'
),
(
  'media', 'MediaAI', 'media-ai',
  'media',
  'Génère, upscale et recherche des médias via Replicate et Pexels',
  '1.0.0', null, null,
  '["image_generation","upscaling","pexels_search"]',
  null, false, 'replicate'
),
(
  'electron', 'ElectronAI', 'electron-ai',
  'desktop',
  'Génère les fichiers Electron pour apps desktop',
  '1.0.0', 'anthropic', 'claude-sonnet-4-5',
  '["electron_main","preload","package_json","installer"]',
  null, false, null
)
ON CONFLICT (agent_id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  model = EXCLUDED.model,
  updated_at = NOW();
