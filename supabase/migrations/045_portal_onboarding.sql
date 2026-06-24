-- supabase/migrations/045_portal_onboarding.sql
-- Onboarding Portail Client — MAJ62

-- 1. Colonnes onboarding sur portal_clients
ALTER TABLE public.portal_clients
  ADD COLUMN IF NOT EXISTS first_login_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS onboarding_done BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS management_plan VARCHAR(20) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255),
  ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS welcome_email_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS site_url VARCHAR(500);

-- Valeurs management_plan :
-- NULL → pas encore choisi
-- 'autonome' → client gère seul (portail Essentiel/Business/Studio)
-- 'gere' → Mat gère — abonnement Maintenance CapCore 49 EUR/mois

-- 2. Index
CREATE INDEX IF NOT EXISTS idx_portal_clients_reset_token
  ON public.portal_clients(password_reset_token);
CREATE INDEX IF NOT EXISTS idx_portal_clients_onboarding
  ON public.portal_clients(onboarding_done);

-- 3. Table portal_management_plans — abonnement gestion déléguée
CREATE TABLE IF NOT EXISTS public.portal_management_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES public.portal_clients(id) ON DELETE CASCADE,
  plan_type VARCHAR(20) NOT NULL DEFAULT 'gere',
  price_eur DECIMAL(10,2) DEFAULT 49.00,
  modifications_per_month INTEGER DEFAULT 2,
  status VARCHAR(20) DEFAULT 'active',
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ends_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_management_client
  ON public.portal_management_plans(client_id);

-- 4. Trigger updated_at
CREATE OR REPLACE FUNCTION update_portal_management_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS portal_management_updated_at ON public.portal_management_plans;
CREATE TRIGGER portal_management_updated_at
  BEFORE UPDATE ON public.portal_management_plans
  FOR EACH ROW EXECUTE FUNCTION update_portal_management_updated_at();

-- 5. RLS (aligné 043)
ALTER TABLE public.portal_management_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access portal_management_plans" ON public.portal_management_plans;
CREATE POLICY "Service role full access portal_management_plans"
  ON public.portal_management_plans FOR ALL USING (true);
