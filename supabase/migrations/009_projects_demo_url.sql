-- URL publique Cloudflare Pages (démo ou vitrine sans gate)

alter table public.projects
  add column if not exists demo_url text;

create index if not exists projects_demo_url_idx
  on public.projects (demo_url)
  where demo_url is not null;
