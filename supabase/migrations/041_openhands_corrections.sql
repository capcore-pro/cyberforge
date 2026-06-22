-- Migration 041 — openhands_corrections
-- Stocke les rapports d'analyse et de correction OpenHands par projet

CREATE TABLE IF NOT EXISTS public.openhands_corrections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id TEXT NOT NULL,
    iterations INTEGER DEFAULT 0,
    issues_found JSONB DEFAULT '[]',
    corrections_applied JSONB DEFAULT '[]',
    quality_score FLOAT DEFAULT 0,
    report JSONB DEFAULT '{}',
    redeployed BOOLEAN DEFAULT FALSE,
    deploy_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_openhands_project_id ON public.openhands_corrections(project_id);
CREATE INDEX IF NOT EXISTS idx_openhands_created_at ON public.openhands_corrections(created_at DESC);

-- RLS
ALTER TABLE public.openhands_corrections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON public.openhands_corrections;
CREATE POLICY "Service role full access" ON public.openhands_corrections
    FOR ALL USING (true);
