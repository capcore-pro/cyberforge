-- Migration 047 — Galerie poses avatar persistante
-- Table stockant les poses FLUX générées par user

CREATE TABLE IF NOT EXISTS pose_gallery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    pose_key TEXT NOT NULL,
    image_url TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pose_gallery_user_pose_unique UNIQUE (user_id, pose_key)
);

ALTER TABLE pose_gallery ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pose_gallery_user_own"
    ON pose_gallery
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Index pour les lectures par user
CREATE INDEX IF NOT EXISTS pose_gallery_user_id_idx ON pose_gallery(user_id);
