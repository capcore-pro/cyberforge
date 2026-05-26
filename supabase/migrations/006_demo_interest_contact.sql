-- Contact formulaire CapCore : horodatage, détails client, accusé de lecture CyberForge

alter table public.demos
  add column if not exists interested_at timestamptz;

alter table public.demos
  add column if not exists interest_seen_at timestamptz;

alter table public.demos
  add column if not exists interest_contact jsonb;

create index if not exists demos_interest_unread_idx
  on public.demos (interested_at desc)
  where status = 'interessee' and interest_seen_at is null;
