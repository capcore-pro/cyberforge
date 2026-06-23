-- Migration 043 — Portail Client client.capcore.pro
-- Tables portal_clients, portal_sites, portal_edits

CREATE TABLE IF NOT EXISTS public.portal_clients (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    full_name TEXT,
    company TEXT,
    plan TEXT DEFAULT 'starter'
        CHECK (plan IN ('starter', 'pro', 'agency')),
    is_active BOOLEAN DEFAULT TRUE,
    supabase_user_id UUID,
    created_by TEXT DEFAULT 'mat',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.portal_sites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES public.portal_clients(id) ON DELETE CASCADE,
    project_id TEXT,
    site_name TEXT NOT NULL,
    site_url TEXT,
    cloudflare_project_name TEXT,
    html_content TEXT,
    html_backup TEXT,
    sector TEXT,
    project_type TEXT DEFAULT 'vitrine_next',
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'draft', 'suspended')),
    last_deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.portal_edits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    site_id UUID REFERENCES public.portal_sites(id) ON DELETE CASCADE,
    client_id UUID REFERENCES public.portal_clients(id) ON DELETE CASCADE,
    edit_type TEXT DEFAULT 'text'
        CHECK (edit_type IN ('text', 'image', 'color', 'section')),
    element_selector TEXT,
    old_value TEXT,
    new_value TEXT,
    deployed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_clients_email
    ON public.portal_clients(email);
CREATE INDEX IF NOT EXISTS idx_portal_sites_client_id
    ON public.portal_sites(client_id);
CREATE INDEX IF NOT EXISTS idx_portal_edits_site_id
    ON public.portal_edits(site_id);

ALTER TABLE public.portal_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portal_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portal_edits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access portal_clients" ON public.portal_clients;
CREATE POLICY "Service role full access portal_clients"
    ON public.portal_clients FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role full access portal_sites" ON public.portal_sites;
CREATE POLICY "Service role full access portal_sites"
    ON public.portal_sites FOR ALL USING (true);

DROP POLICY IF EXISTS "Service role full access portal_edits" ON public.portal_edits;
CREATE POLICY "Service role full access portal_edits"
    ON public.portal_edits FOR ALL USING (true);
