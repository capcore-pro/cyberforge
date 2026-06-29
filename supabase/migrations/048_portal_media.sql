-- Migration 048 — Médiathèque photos client portail (Cloudflare R2)

CREATE TABLE IF NOT EXISTS portal_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES portal_clients(id) ON DELETE CASCADE,
    site_id UUID REFERENCES portal_sites(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    r2_key TEXT NOT NULL,
    r2_url TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes INTEGER,
    uploaded_by TEXT NOT NULL DEFAULT 'client',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS portal_media_client_id_idx
    ON portal_media(client_id);

ALTER TABLE portal_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "portal_media_open" ON portal_media
    FOR ALL USING (true) WITH CHECK (true);
