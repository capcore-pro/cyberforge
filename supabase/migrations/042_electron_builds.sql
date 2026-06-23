-- Migration 042 — electron_builds + electron_licenses
-- Logiciels Desktop clients générés par CyberForge

CREATE TABLE IF NOT EXISTS public.electron_builds (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    client_email TEXT,
    app_name TEXT NOT NULL,
    app_description TEXT,
    project_type TEXT DEFAULT 'desktop',
    model TEXT NOT NULL CHECK (model IN ('one_shot', 'subscription')),
    price_one_shot FLOAT DEFAULT 0,
    price_monthly FLOAT DEFAULT 0,
    github_repo TEXT,
    github_run_id TEXT,
    build_status TEXT DEFAULT 'pending'
        CHECK (build_status IN ('pending', 'building', 'success', 'failed')),
    download_url TEXT,
    version TEXT DEFAULT '1.0.0',
    license_key TEXT UNIQUE,
    stripe_subscription_id TEXT,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.electron_licenses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    build_id UUID REFERENCES public.electron_builds(id) ON DELETE CASCADE,
    client_email TEXT NOT NULL,
    license_key TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL CHECK (model IN ('one_shot', 'subscription')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_check TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_electron_builds_project_id
    ON public.electron_builds(project_id);
CREATE INDEX IF NOT EXISTS idx_electron_builds_status
    ON public.electron_builds(build_status);
CREATE INDEX IF NOT EXISTS idx_electron_licenses_key
    ON public.electron_licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_electron_licenses_email
    ON public.electron_licenses(client_email);

ALTER TABLE public.electron_builds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.electron_licenses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access builds" ON public.electron_builds;
CREATE POLICY "Service role full access builds" ON public.electron_builds
    FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role full access licenses" ON public.electron_licenses;
CREATE POLICY "Service role full access licenses" ON public.electron_licenses
    FOR ALL USING (true);
