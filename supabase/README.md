# Supabase — CyberForge

## Migration

1. Créez un projet sur [supabase.com](https://supabase.com).
2. Ouvrez **SQL Editor** et exécutez les migrations dans l'ordre :
   - `migrations/001_projects_generations.sql`
   - `migrations/002_demos.sql`
   - `migrations/003_generations_preview_html.sql`
   - `migrations/004_clients_table_fr.sql` (table `clients` + lien démos)
   - `migrations/005_clients_address_siret_actif.sql` (adresse, SIRET, actif, lien fiche légale)
   - `migrations/006_demo_interest_contact.sql` (notifications contact démo)
   - `migrations/007_cms_content.sql` (blocs CMS client par projet)
   - `migrations/008_managed_projects_cms_enabled.sql` (toggle mode CMS par projet)
3. Copiez dans `backend/.env` :
   - `SUPABASE_URL` — URL du projet (Settings → API)
   - `SUPABASE_ANON_KEY` — clé anon (référence future ; le frontend passe par FastAPI)
   - `SUPABASE_SECRET_KEY` — clé `service_role` (backend uniquement, ne jamais exposer au renderer)

Redémarrez le backend FastAPI après configuration.
