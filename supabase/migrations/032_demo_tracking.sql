-- Tracker de vues démos — analytics par projet

CREATE TABLE IF NOT EXISTS public.demo_views (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  demo_url TEXT NOT NULL,
  visitor_ip VARCHAR(45),
  user_agent TEXT,
  referer TEXT,
  device_type VARCHAR(50),
  duration_seconds INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_demo_views_project
  ON public.demo_views (project_id);

CREATE INDEX IF NOT EXISTS idx_demo_views_created
  ON public.demo_views (created_at DESC);

ALTER TABLE public.demo_views ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_demo_views" ON public.demo_views;
CREATE POLICY "service_role_all_demo_views"
  ON public.demo_views
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
