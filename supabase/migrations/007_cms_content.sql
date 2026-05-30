-- CyberForge P18 — contenu CMS client (blocs éditables par projet)

create table if not exists public.cms_content (
  id uuid default gen_random_uuid() primary key,
  project_id text not null,
  block_key text not null,
  block_type text not null check (block_type in ('text', 'image', 'color', 'url')),
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz default now(),
  unique (project_id, block_key)
);

create index if not exists cms_content_project_id_idx
  on public.cms_content (project_id);

create index if not exists cms_content_updated_at_idx
  on public.cms_content (project_id, updated_at desc);

alter table public.cms_content enable row level security;

drop policy if exists "service_role_all_cms_content" on public.cms_content;
create policy "service_role_all_cms_content"
  on public.cms_content
  for all
  to service_role
  using (true)
  with check (true);

notify pgrst, 'reload schema';
