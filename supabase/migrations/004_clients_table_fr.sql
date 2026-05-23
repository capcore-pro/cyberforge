-- CyberForge — table clients (colonnes FR) + lien démos

create table if not exists public.clients (
  id uuid default gen_random_uuid() primary key,
  nom text not null,
  entreprise text,
  email text,
  telephone text,
  couleur text default '#6366f1',
  logo_url text,
  est_perso boolean default false,
  created_at timestamptz default now()
);

create index if not exists clients_created_at_idx on public.clients (created_at desc);
create index if not exists clients_est_perso_idx on public.clients (est_perso);

alter table public.clients enable row level security;

drop policy if exists "service_role_all_clients" on public.clients;
create policy "service_role_all_clients"
  on public.clients
  for all
  to service_role
  using (true)
  with check (true);

alter table public.demos
  add column if not exists client_id uuid references public.clients (id) on delete set null;

alter table public.demos
  add column if not exists status text not null default 'envoyee';

alter table public.demos
  add column if not exists opened_at timestamptz;

alter table public.demos
  drop constraint if exists demos_status_check;

alter table public.demos
  add constraint demos_status_check
  check (status in ('envoyee', 'ouverte', 'validee', 'expiree'));

create index if not exists demos_client_id_idx on public.demos (client_id);

notify pgrst, 'reload schema';
