-- Aperçu HTML statique par génération (pour cartes Projets et démos)
alter table public.generations
  add column if not exists preview_html text;
