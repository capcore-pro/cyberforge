-- CyberForge — Workflow Engine (définitions, étapes, exécutions)
-- 5 workflows pipeline V2 seedés

CREATE TABLE IF NOT EXISTS workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  workflow_type VARCHAR(100) NOT NULL,
  project_types JSONB DEFAULT '[]',
  version VARCHAR(50) DEFAULT '1.0.0',
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL
    REFERENCES workflows(id) ON DELETE CASCADE,
  step_name VARCHAR(255) NOT NULL,
  step_type VARCHAR(100) NOT NULL,
  agent_id VARCHAR(100),
  tool_id VARCHAR(100),
  execution_order INTEGER NOT NULL,
  is_optional BOOLEAN DEFAULT FALSE,
  condition_field VARCHAR(100),
  condition_values JSONB DEFAULT '[]',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_steps_workflow
ON workflow_steps(workflow_id);

CREATE INDEX IF NOT EXISTS idx_wf_steps_order
ON workflow_steps(workflow_id, execution_order);

CREATE TABLE IF NOT EXISTS workflow_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL
    REFERENCES workflows(id),
  generation_id VARCHAR(255),
  project_id UUID,
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  status VARCHAR(50) DEFAULT 'pending',
  current_step VARCHAR(100),
  total_steps INTEGER DEFAULT 0,
  completed_steps INTEGER DEFAULT 0,
  total_cost_usd DECIMAL(12,6) DEFAULT 0,
  total_tokens BIGINT DEFAULT 0,
  duration_ms BIGINT DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_exec_generation
ON workflow_executions(generation_id);

CREATE INDEX IF NOT EXISTS idx_wf_exec_project
ON workflow_executions(project_id);

CREATE INDEX IF NOT EXISTS idx_wf_exec_status
ON workflow_executions(status);

INSERT INTO workflows (
  workflow_id, name, description,
  workflow_type, project_types, version
) VALUES
(
  'vitrine_simple',
  'Vitrine Simple',
  'Génération site vitrine — chemin le plus court',
  'generation',
  '["vitrine_next"]',
  '2.0.0'
),
(
  'ecommerce',
  'E-commerce',
  'Génération boutique avec panier et Stripe',
  'generation',
  '["ecommerce"]',
  '2.0.0'
),
(
  'reservation',
  'Site Réservation',
  'Génération site réservation avec calendrier',
  'generation',
  '["site_reservation"]',
  '2.0.0'
),
(
  'app_web_crm',
  'App Web / CRM',
  'Génération application web ou CRM avec auth',
  'generation',
  '["application_web", "crm", "real_app"]',
  '2.0.0'
),
(
  'extension_navigateur',
  'Extension Navigateur',
  'Génération extension Chrome MV3',
  'generation',
  '["extension_navigateur"]',
  '2.0.0'
)
ON CONFLICT (workflow_id) DO UPDATE SET
  name = EXCLUDED.name,
  updated_at = NOW();

-- Vitrine simple (5 étapes)
INSERT INTO workflow_steps (
  workflow_id, step_name, step_type,
  agent_id, execution_order, is_optional
)
SELECT w.id, s.step_name, s.step_type,
       s.agent_id, s.exec_order, s.optional
FROM workflows w
CROSS JOIN (VALUES
  ('BriefAI', 'agent', 'brief', 1, false),
  ('DesignSystemAI', 'agent', 'design_system', 2, false),
  ('GeneratorAI', 'agent', 'generator', 3, false),
  ('SupervisorAI', 'agent', 'supervisor', 4, false),
  ('DeployAI', 'agent', 'deploy', 5, false)
) AS s(step_name, step_type, agent_id, exec_order, optional)
WHERE w.workflow_id = 'vitrine_simple'
  AND NOT EXISTS (
    SELECT 1 FROM workflow_steps ws WHERE ws.workflow_id = w.id
  );

-- E-commerce (7 étapes)
INSERT INTO workflow_steps (
  workflow_id, step_name, step_type,
  agent_id, execution_order, is_optional,
  condition_field, condition_values
)
SELECT w.id, s.step_name, s.step_type,
       s.agent_id, s.exec_order, s.optional,
       s.cond_field, s.cond_values::jsonb
FROM workflows w
CROSS JOIN (VALUES
  ('BriefAI', 'agent', 'brief', 1, false, NULL, '[]'),
  ('DesignSystemAI', 'agent', 'design_system', 2, false, NULL, '[]'),
  ('DatabaseAI', 'agent', 'database', 3, false, NULL, '[]'),
  ('PaymentAI', 'agent', 'payment', 4, false, NULL, '[]'),
  ('GeneratorAI', 'agent', 'generator', 5, false, NULL, '[]'),
  ('SupervisorAI', 'agent', 'supervisor', 6, false, NULL, '[]'),
  ('DeployAI', 'agent', 'deploy', 7, false, NULL, '[]')
) AS s(step_name, step_type, agent_id, exec_order, optional, cond_field, cond_values)
WHERE w.workflow_id = 'ecommerce'
  AND NOT EXISTS (
    SELECT 1 FROM workflow_steps ws WHERE ws.workflow_id = w.id
  );

-- Réservation (7 étapes — même squelette que e-commerce)
INSERT INTO workflow_steps (
  workflow_id, step_name, step_type,
  agent_id, execution_order, is_optional,
  condition_field, condition_values
)
SELECT w.id, s.step_name, s.step_type,
       s.agent_id, s.exec_order, s.optional,
       s.cond_field, s.cond_values::jsonb
FROM workflows w
CROSS JOIN (VALUES
  ('BriefAI', 'agent', 'brief', 1, false, NULL, '[]'),
  ('DesignSystemAI', 'agent', 'design_system', 2, false, NULL, '[]'),
  ('DatabaseAI', 'agent', 'database', 3, false, NULL, '[]'),
  ('PaymentAI', 'agent', 'payment', 4, false, NULL, '[]'),
  ('GeneratorAI', 'agent', 'generator', 5, false, NULL, '[]'),
  ('SupervisorAI', 'agent', 'supervisor', 6, false, NULL, '[]'),
  ('DeployAI', 'agent', 'deploy', 7, false, NULL, '[]')
) AS s(step_name, step_type, agent_id, exec_order, optional, cond_field, cond_values)
WHERE w.workflow_id = 'reservation'
  AND NOT EXISTS (
    SELECT 1 FROM workflow_steps ws WHERE ws.workflow_id = w.id
  );

-- App web / CRM (7 étapes)
INSERT INTO workflow_steps (
  workflow_id, step_name, step_type,
  agent_id, execution_order, is_optional
)
SELECT w.id, s.step_name, s.step_type,
       s.agent_id, s.exec_order, s.optional
FROM workflows w
CROSS JOIN (VALUES
  ('BriefAI', 'agent', 'brief', 1, false),
  ('DesignSystemAI', 'agent', 'design_system', 2, false),
  ('DatabaseAI', 'agent', 'database', 3, false),
  ('AuthAI', 'agent', 'auth', 4, false),
  ('GeneratorAI', 'agent', 'generator', 5, false),
  ('SupervisorAI', 'agent', 'supervisor', 6, false),
  ('DeployAI', 'agent', 'deploy', 7, false)
) AS s(step_name, step_type, agent_id, exec_order, optional)
WHERE w.workflow_id = 'app_web_crm'
  AND NOT EXISTS (
    SELECT 1 FROM workflow_steps ws WHERE ws.workflow_id = w.id
  );

-- Extension navigateur (3 étapes)
INSERT INTO workflow_steps (
  workflow_id, step_name, step_type,
  agent_id, execution_order, is_optional
)
SELECT w.id, s.step_name, s.step_type,
       s.agent_id, s.exec_order, s.optional
FROM workflows w
CROSS JOIN (VALUES
  ('BriefAI', 'agent', 'brief', 1, false),
  ('ExtensionBuilder', 'agent', 'extension_builder', 2, false),
  ('DeployAI', 'agent', 'deploy', 3, false)
) AS s(step_name, step_type, agent_id, exec_order, optional)
WHERE w.workflow_id = 'extension_navigateur'
  AND NOT EXISTS (
    SELECT 1 FROM workflow_steps ws WHERE ws.workflow_id = w.id
  );
