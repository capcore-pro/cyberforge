ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS price_eur DECIMAL(10,2),
  ADD COLUMN IF NOT EXISTS price_paid_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS price_notes TEXT;

CREATE INDEX IF NOT EXISTS idx_projects_price_eur ON projects(price_eur);
CREATE INDEX IF NOT EXISTS idx_projects_price_paid_at ON projects(price_paid_at);
