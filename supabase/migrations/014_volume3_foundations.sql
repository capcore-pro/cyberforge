-- CyberForge — Volume 3 foundations (agent executions, audit, prompts, templates, RBAC)
-- Exécuter dans l'éditeur SQL Supabase ou via supabase db push

-- 1. Agent Executions
CREATE TABLE IF NOT EXISTS agent_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  generation_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  agent_name VARCHAR(100) NOT NULL,
  agent_slug VARCHAR(100),
  execution_type VARCHAR(100) DEFAULT 'generation',
  status VARCHAR(50) DEFAULT 'pending',
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  execution_cost DECIMAL(12,6) DEFAULT 0,
  duration_ms BIGINT DEFAULT 0,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_exec_project
ON agent_executions(project_id);

CREATE INDEX IF NOT EXISTS idx_agent_exec_agent
ON agent_executions(agent_name);

CREATE INDEX IF NOT EXISTS idx_agent_exec_status
ON agent_executions(status);

CREATE INDEX IF NOT EXISTS idx_agent_exec_created
ON agent_executions(created_at DESC);

-- 2. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  actor_type VARCHAR(100) NOT NULL,
  actor_id VARCHAR(255),
  event_type VARCHAR(255) NOT NULL,
  event_data JSONB,
  project_id UUID,
  ip_address VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type
ON audit_logs(event_type);

CREATE INDEX IF NOT EXISTS idx_audit_project
ON audit_logs(project_id);

CREATE INDEX IF NOT EXISTS idx_audit_created
ON audit_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_actor
ON audit_logs(actor_type, actor_id);

-- 3. Prompt Categories
CREATE TABLE IF NOT EXISTS prompt_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO prompt_categories (id, name, slug) VALUES
  (gen_random_uuid(), 'System', 'system'),
  (gen_random_uuid(), 'Business', 'business'),
  (gen_random_uuid(), 'Design', 'design'),
  (gen_random_uuid(), 'Frontend', 'frontend'),
  (gen_random_uuid(), 'Backend', 'backend'),
  (gen_random_uuid(), 'Database', 'database'),
  (gen_random_uuid(), 'SEO', 'seo'),
  (gen_random_uuid(), 'Media', 'media'),
  (gen_random_uuid(), 'Deployment', 'deployment'),
  (gen_random_uuid(), 'Security', 'security')
ON CONFLICT (slug) DO NOTHING;

-- 4. Prompts
CREATE TABLE IF NOT EXISTS prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID
    REFERENCES prompt_categories(id),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  content TEXT NOT NULL,
  version VARCHAR(50) DEFAULT '1.0.0',
  status VARCHAR(50) DEFAULT 'active',
  agent_slug VARCHAR(100),
  quality_score INTEGER DEFAULT 0,
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompts_category
ON prompts(category_id);

CREATE INDEX IF NOT EXISTS idx_prompts_agent
ON prompts(agent_slug);

CREATE INDEX IF NOT EXISTS idx_prompts_status
ON prompts(status);

-- 5. Prompt Versions
CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID NOT NULL
    REFERENCES prompts(id) ON DELETE CASCADE,
  version VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  changelog TEXT,
  quality_score INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt
ON prompt_versions(prompt_id);

-- 6. Templates
CREATE TABLE IF NOT EXISTS templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  template_type VARCHAR(100),
  industry VARCHAR(100),
  project_type VARCHAR(50),
  version VARCHAR(50) DEFAULT '1.0.0',
  configuration JSONB,
  status VARCHAR(50) DEFAULT 'active',
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_type
ON templates(template_type);

CREATE INDEX IF NOT EXISTS idx_templates_industry
ON templates(industry);

CREATE INDEX IF NOT EXISTS idx_templates_project_type
ON templates(project_type);

-- 7. Template Versions
CREATE TABLE IF NOT EXISTS template_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID NOT NULL
    REFERENCES templates(id) ON DELETE CASCADE,
  version VARCHAR(50) NOT NULL,
  configuration JSONB,
  changelog TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 8. Roles
CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO roles (name, description) VALUES
  ('owner', 'Propriétaire — accès total'),
  ('admin', 'Administrateur — gestion complète'),
  ('developer', 'Développeur — génération et déploiement'),
  ('viewer', 'Lecteur — consultation uniquement'),
  ('agent', 'Agent IA — exécution automatisée')
ON CONFLICT (name) DO NOTHING;

-- 9. Permissions
CREATE TABLE IF NOT EXISTS permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) UNIQUE NOT NULL,
  description TEXT
);

INSERT INTO permissions (name, description) VALUES
  ('project.read', 'Lire les projets'),
  ('project.write', 'Créer et modifier les projets'),
  ('project.delete', 'Supprimer les projets'),
  ('agent.execute', 'Exécuter les agents'),
  ('agent.manage', 'Gérer les agents'),
  ('deployment.execute', 'Déployer les projets'),
  ('knowledge.manage', 'Gérer la base de connaissance'),
  ('memory.manage', 'Gérer la mémoire'),
  ('prompt.manage', 'Gérer les prompts'),
  ('template.manage', 'Gérer les templates')
ON CONFLICT (name) DO NOTHING;

-- 10. Role Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
  role_id UUID NOT NULL
    REFERENCES roles(id),
  permission_id UUID NOT NULL
    REFERENCES permissions(id),
  PRIMARY KEY (role_id, permission_id)
);

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'owner'
ON CONFLICT DO NOTHING;

ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_agent_executions"
  ON agent_executions FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_audit_logs"
  ON audit_logs FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_prompt_categories"
  ON prompt_categories FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_prompts"
  ON prompts FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_prompt_versions"
  ON prompt_versions FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_templates"
  ON templates FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_template_versions"
  ON template_versions FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_roles"
  ON roles FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_permissions"
  ON permissions FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_role_permissions"
  ON role_permissions FOR ALL TO service_role
  USING (true) WITH CHECK (true);
