-- Mode Client — lien de validation démo (review publique)

CREATE TABLE IF NOT EXISTS public.client_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  token VARCHAR(64) NOT NULL UNIQUE,
  client_name VARCHAR(255),
  client_email VARCHAR(255),
  status VARCHAR(50) DEFAULT 'pending',
  feedback TEXT,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  viewed_at TIMESTAMPTZ,
  responded_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_token
  ON public.client_reviews (token);

CREATE INDEX IF NOT EXISTS idx_reviews_project
  ON public.client_reviews (project_id);

ALTER TABLE public.client_reviews ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_client_reviews" ON public.client_reviews;
CREATE POLICY "service_role_all_client_reviews"
  ON public.client_reviews
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
