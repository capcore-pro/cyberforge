"""Client Supabase service role — tables portal_* et accès admin."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from config import get_settings, plain_secret_str


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    settings = get_settings()
    url = (settings.supabase_url or "").strip()
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        raise RuntimeError("Supabase non configuré (SUPABASE_URL / SUPABASE_SECRET_KEY).")
    return create_client(url, key)
