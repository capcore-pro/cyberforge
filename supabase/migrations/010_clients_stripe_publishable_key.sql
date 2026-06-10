-- Clé Stripe publishable client (pk_test_ / pk_live_) — jamais la clé secrète.

alter table public.clients
  add column if not exists stripe_publishable_key text;
