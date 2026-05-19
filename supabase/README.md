# Supabase — CyberForge

## Migration

1. Créez un projet sur [supabase.com](https://supabase.com).
2. Ouvrez **SQL Editor** et exécutez le fichier `migrations/001_projects_generations.sql`.
3. Copiez dans `backend/.env` :
   - `SUPABASE_URL` — URL du projet (Settings → API)
   - `SUPABASE_ANON_KEY` — clé anon (référence future ; le frontend passe par FastAPI)
   - `SUPABASE_SECRET_KEY` — clé `service_role` (backend uniquement, ne jamais exposer au renderer)

Redémarrez le backend FastAPI après configuration.
