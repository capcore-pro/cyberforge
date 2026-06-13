-- CyberForge — Pipeline Commercial (prospects + interactions)

CREATE TABLE IF NOT EXISTS prospects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL
    DEFAULT '00000000-0000-0000-0000-000000000001',
  nom VARCHAR(255) NOT NULL,
  entreprise VARCHAR(255),
  email VARCHAR(255),
  telephone VARCHAR(50),
  secteur VARCHAR(100),
  source VARCHAR(100) DEFAULT 'manuel',
  statut VARCHAR(50) DEFAULT 'nouveau',
  valeur_estimee DECIMAL(10,2) DEFAULT 0,
  notes TEXT,
  demo_url TEXT,
  contact_date TIMESTAMP,
  relance_date TIMESTAMP,
  closed_date TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospects_statut
ON prospects(statut);

CREATE INDEX IF NOT EXISTS idx_prospects_created
ON prospects(created_at DESC);

CREATE TABLE IF NOT EXISTS prospect_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prospect_id UUID NOT NULL
    REFERENCES prospects(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interactions_prospect
ON prospect_interactions(prospect_id);
