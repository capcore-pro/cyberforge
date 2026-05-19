-- CyberForge — projets et générations CoreMindAI
-- Exécuter dans l'éditeur SQL Supabase ou via supabase db push

create extension if not exists "pgcrypto";

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  prompt text not null,
  project_type text not null,
  summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.generations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  prompt text not null,
  project_type text not null,
  model text not null,
  provider text not null,
  complexity text not null,
  complexity_score integer not null check (complexity_score between 1 and 10),
  duration_ms integer not null default 0 check (duration_ms >= 0),
  estimated_cost_usd numeric(12, 6) not null default 0,
  code text not null,
  files jsonb not null default '[]'::jsonb,
  stack jsonb not null default '[]'::jsonb,
  analysis jsonb not null default '{}'::jsonb,
  generation_summary text,
  planned_models jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists projects_created_at_idx
  on public.projects (created_at desc);

create index if not exists projects_prompt_type_idx
  on public.projects (prompt, project_type);

create index if not exists generations_project_id_idx
  on public.generations (project_id);

create index if not exists generations_created_at_idx
  on public.generations (created_at desc);

create or replace function public.set_projects_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists projects_updated_at on public.projects;
create trigger projects_updated_at
  before update on public.projects
  for each row
  execute function public.set_projects_updated_at();

alter table public.projects enable row level security;
alter table public.generations enable row level security;

-- Accès service_role (backend) uniquement ; pas d'accès anon direct aux données.
create policy "service_role_all_projects"
  on public.projects
  for all
  to service_role
  using (true)
  with check (true);

create policy "service_role_all_generations"
  on public.generations
  for all
  to service_role
  using (true)
  with check (true);
