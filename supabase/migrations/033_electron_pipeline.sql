-- Active ElectronAI dans le pipeline CyberForge

UPDATE public.agents
SET
  in_pipeline = true,
  description = 'Génère les fichiers Electron pour apps desktop Windows (.exe)',
  updated_at = NOW()
WHERE agent_id = 'electron';
