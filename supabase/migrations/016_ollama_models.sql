-- Seed modèles Ollama (coût local = 0)

INSERT INTO llm_models
  (provider_id, model_name, model_slug,
   context_window,
   input_cost_per_million, output_cost_per_million,
   capabilities)
SELECT
  p.id,
  m.model_name, m.model_slug,
  m.context_window,
  m.input_cost, m.output_cost,
  m.capabilities::jsonb
FROM llm_providers p
JOIN (VALUES
  ('qwen3', 'qwen3',
   32000, 0, 0,
   '["chat","analysis","local","fast"]'),
  ('llama3.2', 'llama3.2',
   128000, 0, 0,
   '["chat","analysis","local"]')
) AS m(model_name, model_slug,
       context_window, input_cost, output_cost,
       capabilities)
ON (p.slug = 'ollama')
ON CONFLICT (model_slug) DO NOTHING;
