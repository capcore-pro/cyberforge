-- MIGRATION 040 — scenes_data sur commandes vidéo client

ALTER TABLE video_client_orders
  ADD COLUMN IF NOT EXISTS scenes_data JSONB DEFAULT '[]';
