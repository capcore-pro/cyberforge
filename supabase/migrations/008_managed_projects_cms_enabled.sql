-- CyberForge P18 — mode CMS client activable par projet managé

alter table public.managed_projects
  add column if not exists cms_enabled boolean not null default true;

create index if not exists managed_projects_cms_enabled_idx
  on public.managed_projects (cms_enabled)
  where deleted_at is null;

notify pgrst, 'reload schema';
