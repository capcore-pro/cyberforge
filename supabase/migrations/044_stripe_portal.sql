-- supabase/migrations/044_stripe_portal.sql
-- Stripe abonnements Portail Client — MAJ61

-- 1. Colonnes Stripe sur portal_clients
ALTER TABLE public.portal_clients
  ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'trial',
  ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
  ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS billing_interval VARCHAR(10) DEFAULT 'monthly';

-- plan existe déjà (043) — nouveau schéma Stripe
ALTER TABLE public.portal_clients
  DROP CONSTRAINT IF EXISTS portal_clients_plan_check;

ALTER TABLE public.portal_clients
  ALTER COLUMN plan SET DEFAULT 'trial';

-- Valeurs possibles :
-- plan : 'trial' | 'essentiel' | 'business' | 'studio'
-- subscription_status : 'trial' | 'active' | 'expired' | 'canceled' | 'none'
-- billing_interval : 'monthly' | 'yearly'

-- 2. Table portal_subscriptions — historique complet
CREATE TABLE IF NOT EXISTS public.portal_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES public.portal_clients(id) ON DELETE CASCADE,
  stripe_subscription_id VARCHAR(255),
  stripe_customer_id VARCHAR(255),
  stripe_invoice_id VARCHAR(255),
  plan VARCHAR(20) NOT NULL,
  billing_interval VARCHAR(10) NOT NULL DEFAULT 'monthly',
  status VARCHAR(20) NOT NULL,
  amount_eur DECIMAL(10,2),
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  canceled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Index
CREATE INDEX IF NOT EXISTS idx_portal_subscriptions_client_id ON public.portal_subscriptions(client_id);
CREATE INDEX IF NOT EXISTS idx_portal_subscriptions_stripe_sub ON public.portal_subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_portal_clients_stripe_customer ON public.portal_clients(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_portal_clients_status ON public.portal_clients(subscription_status);

-- 4. Trigger updated_at
CREATE OR REPLACE FUNCTION update_portal_subscriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS portal_subscriptions_updated_at ON public.portal_subscriptions;
CREATE TRIGGER portal_subscriptions_updated_at
  BEFORE UPDATE ON public.portal_subscriptions
  FOR EACH ROW EXECUTE FUNCTION update_portal_subscriptions_updated_at();

-- 5. Mettre tous les clients existants en trial 14 jours
UPDATE public.portal_clients
SET
  plan = 'trial',
  subscription_status = 'trial',
  trial_ends_at = NOW() + INTERVAL '14 days'
WHERE subscription_status IS NULL OR subscription_status = 'trial';

-- 6. RLS (aligné 043)
ALTER TABLE public.portal_subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access portal_subscriptions" ON public.portal_subscriptions;
CREATE POLICY "Service role full access portal_subscriptions"
  ON public.portal_subscriptions FOR ALL USING (true);
