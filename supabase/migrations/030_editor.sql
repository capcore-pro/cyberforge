-- Éditeur inline CyberForge — historique des éditions manuelles

ALTER TABLE public.generations
  ADD COLUMN IF NOT EXISTS edited_html TEXT,
  ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS edit_count INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS public.editor_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  generation_id UUID NOT NULL,
  html_before TEXT,
  html_after TEXT,
  edit_type VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_editor_history_project
  ON public.editor_history (project_id);

ALTER TABLE public.editor_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all_editor_history" ON public.editor_history;
CREATE POLICY "service_role_all_editor_history"
  ON public.editor_history
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
