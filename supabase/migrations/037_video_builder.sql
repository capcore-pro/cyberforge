-- ============================================
-- MIGRATION 037 — VIDEO BUILDER
-- CyberForge — 17/06/2026
-- ============================================

-- TABLE PROJETS VIDÉO
CREATE TABLE IF NOT EXISTS video_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  brand TEXT NOT NULL DEFAULT 'cyberforge',
  brief TEXT,
  ambiance TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  scenes JSONB NOT NULL DEFAULT '[]',
  music_url TEXT,
  music_name TEXT,
  final_video_url TEXT,
  kling_cost_units INTEGER NOT NULL DEFAULT 0,
  total_duration FLOAT DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT status_check CHECK (
    status IN ('draft','generating','assembling','done','failed')
  ),
  CONSTRAINT brand_check CHECK (
    brand IN ('cyberforge','capcopy','lumio','vocali')
  )
);

-- TABLE CLIPS INDIVIDUELS
CREATE TABLE IF NOT EXISTS video_clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES video_projects(id) ON DELETE CASCADE,
  scene_number INTEGER NOT NULL,
  title TEXT,
  prompt TEXT NOT NULL,
  camera_move TEXT,
  mood TEXT,
  kling_task_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  clip_url TEXT,
  local_path TEXT,
  duration FLOAT,
  units_used INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT clip_status_check CHECK (
    status IN ('pending','processing','done','failed')
  )
);

-- TABLE SOLDE KLING
CREATE TABLE IF NOT EXISTS kling_balance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  units_total INTEGER NOT NULL DEFAULT 0,
  units_used INTEGER NOT NULL DEFAULT 0,
  units_remaining INTEGER GENERATED ALWAYS AS (units_total - units_used) STORED,
  last_recharged_at TIMESTAMPTZ,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TABLE MUSIQUES DISPONIBLES
CREATE TABLE IF NOT EXISTS video_music_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  duration FLOAT,
  mood TEXT,
  brand TEXT DEFAULT 'all',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- INSERT SOLDE INITIAL
INSERT INTO kling_balance (units_total, units_used)
VALUES (100, 10)
ON CONFLICT DO NOTHING;

-- INSERT MUSIQUES DE BASE
INSERT INTO video_music_library (name, url, mood, brand) VALUES
('CyberForge Dark Tech', '/music/cyberforge-dark-tech.mp3', 'epic', 'cyberforge'),
('CapCore Premium', '/music/capcore-premium.mp3', 'corporate', 'all'),
('Lumio Soft', '/music/lumio-soft.mp3', 'calm', 'lumio'),
('Vocali Energy', '/music/vocali-energy.mp3', 'energetic', 'vocali')
ON CONFLICT DO NOTHING;

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_video_projects_user 
  ON video_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_video_projects_status 
  ON video_projects(status);
CREATE INDEX IF NOT EXISTS idx_video_clips_project 
  ON video_clips(project_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_status 
  ON video_clips(status);
CREATE INDEX IF NOT EXISTS idx_video_clips_task 
  ON video_clips(kling_task_id);

-- TRIGGERS UPDATED_AT
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER video_projects_updated_at
  BEFORE UPDATE ON video_projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER video_clips_updated_at
  BEFORE UPDATE ON video_clips
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS
ALTER TABLE video_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE kling_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_music_library ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_projects" ON video_projects
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "users_own_clips" ON video_clips
  FOR ALL USING (
    project_id IN (
      SELECT id FROM video_projects WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "balance_read_all" ON kling_balance
  FOR SELECT USING (true);

CREATE POLICY "music_read_all" ON video_music_library
  FOR SELECT USING (true);
