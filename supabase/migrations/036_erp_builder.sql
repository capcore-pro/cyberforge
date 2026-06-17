-- CyberForge — ERP Builder (Odoo / ERPNext / Custom)
-- Table erp_projects pour /api/erp/*

CREATE TABLE IF NOT EXISTS public.erp_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  client_name TEXT,
  erp_type TEXT CHECK (erp_type IN ('odoo', 'erpnext', 'custom')),
  company_size TEXT CHECK (company_size IN ('solo', 'small', 'medium', 'large')),
  budget TEXT CHECK (budget IN ('low', 'medium', 'high')),
  modules JSONB NOT NULL DEFAULT '[]'::jsonb,
  primary_color TEXT DEFAULT '#0f1117',
  logo_url TEXT,
  domain TEXT,
  admin_email TEXT,
  admin_password TEXT,
  docker_compose_content TEXT,
  container_name TEXT,
  port INT,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'configuring', 'installing', 'running', 'error', 'stopped')),
  url TEXT,
  install_logs TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_erp_projects_status ON public.erp_projects (status);
CREATE INDEX IF NOT EXISTS idx_erp_projects_updated ON public.erp_projects (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_erp_projects_erp_type ON public.erp_projects (erp_type);

ALTER TABLE public.erp_projects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_erp_projects" ON public.erp_projects;
CREATE POLICY "service_role_all_erp_projects"
  ON public.erp_projects
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
