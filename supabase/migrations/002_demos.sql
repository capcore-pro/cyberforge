-- CyberForge — démos client partagées (lien + mot de passe temporaire)

create table if not exists public.demos (
  id uuid primary key default gen_random_uuid(),
  token text not null unique,
  password_hash text not null,
  expires_at timestamptz not null,
  duration_hours integer not null check (duration_hours in (24, 48, 168)),
  title text not null,
  payload jsonb not null default '{}'::jsonb,
  generation_id uuid references public.generations (id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists demos_token_idx on public.demos (token);

create index if not exists demos_expires_at_idx on public.demos (expires_at desc);

alter table public.demos enable row level security;

create policy "service_role_all_demos"
  on public.demos
  for all
  to service_role
  using (true)
  with check (true);
