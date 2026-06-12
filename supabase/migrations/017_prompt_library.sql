-- CyberForge — Volume 04D Prompt Library (benchmarks)

CREATE TABLE IF NOT EXISTS prompt_benchmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID NOT NULL
    REFERENCES prompts(id) ON DELETE CASCADE,
  prompt_version VARCHAR(50),
  task_type VARCHAR(100),
  model_used VARCHAR(255),
  provider VARCHAR(100),
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  duration_ms BIGINT DEFAULT 0,
  quality_score INTEGER DEFAULT 0,
  cost_usd DECIMAL(12,6) DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmarks_prompt
ON prompt_benchmarks(prompt_id);

CREATE INDEX IF NOT EXISTS idx_benchmarks_task
ON prompt_benchmarks(task_type);

ALTER TABLE prompt_benchmarks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_prompt_benchmarks"
  ON prompt_benchmarks FOR ALL TO service_role
  USING (true) WITH CHECK (true);
