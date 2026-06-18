-- ============================================
-- MIGRATION 038 — VIDEO CLIENT ORDERS
-- Commandes vidéo clients (brief + estimation + livraison)
-- ============================================

CREATE TABLE IF NOT EXISTS video_client_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Identité client
  client_name TEXT NOT NULL,
  client_email TEXT NOT NULL,
  client_company TEXT,
  client_phone TEXT,

  -- Brief vidéo
  secteur TEXT NOT NULL,
  objectif TEXT NOT NULL,
  ton TEXT NOT NULL,
  produits_services TEXT,
  public_cible TEXT,
  slogan TEXT,
  couleurs_marque TEXT,
  duree_souhaitee INTEGER NOT NULL DEFAULT 30,
  exemples_references TEXT,
  notes_libres TEXT,

  -- Estimation
  nb_scenes INTEGER NOT NULL DEFAULT 5,
  musique_premium BOOLEAN NOT NULL DEFAULT false,
  overlay_texte BOOLEAN NOT NULL DEFAULT true,
  livraison_express BOOLEAN NOT NULL DEFAULT false,
  prix_estime_min INTEGER,
  prix_estime_max INTEGER,

  -- Statut
  status TEXT NOT NULL DEFAULT 'brief_recu',
  video_project_id UUID REFERENCES video_projects(id) ON DELETE SET NULL,

  -- PDF
  pdf_url TEXT,

  CONSTRAINT video_client_orders_status_check CHECK (
    status IN ('brief_recu', 'en_generation', 'livre')
  ),
  CONSTRAINT video_client_orders_duree_check CHECK (duree_souhaitee > 0),
  CONSTRAINT video_client_orders_nb_scenes_check CHECK (nb_scenes > 0)
);

CREATE INDEX IF NOT EXISTS idx_video_client_orders_status
  ON video_client_orders(status);

CREATE INDEX IF NOT EXISTS idx_video_client_orders_email
  ON video_client_orders(client_email);

CREATE INDEX IF NOT EXISTS idx_video_client_orders_created
  ON video_client_orders(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_video_client_orders_project
  ON video_client_orders(video_project_id);

ALTER TABLE video_client_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_video_client_orders"
  ON video_client_orders
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
