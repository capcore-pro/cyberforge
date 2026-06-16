-- CyberForge — Mobile Builder (MobileAI + EAS Build)
-- Tables mobile_apps et mobile_builds pour /api/mobile/*

CREATE TABLE IF NOT EXISTS public.mobile_apps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  mode TEXT NOT NULL CHECK (mode IN ('client', 'product')),
  sector TEXT,
  primary_color TEXT DEFAULT '#06b6d4',
  secondary_color TEXT DEFAULT '#8b5cf6',
  logo_url TEXT,
  app_slug TEXT UNIQUE NOT NULL,
  bundle_id TEXT,
  features JSONB NOT NULL DEFAULT '[]'::jsonb,
  screens JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft',
  eas_build_id TEXT,
  apk_url TEXT,
  build_logs TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.mobile_builds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  app_id UUID NOT NULL REFERENCES public.mobile_apps(id) ON DELETE CASCADE,
  build_number INT NOT NULL DEFAULT 1,
  eas_build_id TEXT,
  platform TEXT NOT NULL DEFAULT 'android',
  status TEXT NOT NULL DEFAULT 'pending',
  apk_url TEXT,
  build_duration_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mobile_apps_slug ON public.mobile_apps (app_slug);
CREATE INDEX IF NOT EXISTS idx_mobile_apps_status ON public.mobile_apps (status);
CREATE INDEX IF NOT EXISTS idx_mobile_apps_updated ON public.mobile_apps (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_mobile_builds_app_id ON public.mobile_builds (app_id);
CREATE INDEX IF NOT EXISTS idx_mobile_builds_created ON public.mobile_builds (created_at DESC);

ALTER TABLE public.mobile_apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mobile_builds ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_mobile_apps" ON public.mobile_apps;
CREATE POLICY "service_role_all_mobile_apps"
  ON public.mobile_apps
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS "service_role_all_mobile_builds" ON public.mobile_builds;
CREATE POLICY "service_role_all_mobile_builds"
  ON public.mobile_builds
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
