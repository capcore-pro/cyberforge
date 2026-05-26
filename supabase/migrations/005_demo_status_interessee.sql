-- Statut « intéressé » — formulaire contact CapCore soumis depuis la démo Cloudflare

alter table public.demos
  drop constraint if exists demos_status_check;

alter table public.demos
  add constraint demos_status_check
  check (status in ('envoyee', 'ouverte', 'validee', 'expiree', 'interessee'));

notify pgrst, 'reload schema';
