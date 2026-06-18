-- ============================================
-- MIGRATION 039 — VIDEO PROJECTS CLIENT LINK
-- Lien projets vidéo ↔ commandes clients
-- ============================================

ALTER TABLE video_projects
  ADD COLUMN IF NOT EXISTS secteur TEXT,
  ADD COLUMN IF NOT EXISTS ton TEXT DEFAULT 'professionnel',
  ADD COLUMN IF NOT EXISTS scenes_data JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS client_order_id UUID REFERENCES video_client_orders(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'internal';

CREATE INDEX IF NOT EXISTS idx_video_projects_client_order
  ON video_projects(client_order_id);

CREATE INDEX IF NOT EXISTS idx_video_projects_source
  ON video_projects(source);
