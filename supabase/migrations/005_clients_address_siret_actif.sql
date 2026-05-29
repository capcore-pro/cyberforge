-- CyberForge — adresse, SIRET, statut actif, lien fiche légale

alter table public.clients
  add column if not exists adresse text,
  add column if not exists siret text,
  add column if not exists actif boolean not null default true,
  add column if not exists legal_client_id text;

create index if not exists clients_actif_idx on public.clients (actif);

notify pgrst, 'reload schema';
