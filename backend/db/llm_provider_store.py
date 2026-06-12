"""
Persistance Supabase — registre LLM providers / modèles.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    get_supabase_store,
)

logger = logging.getLogger(__name__)


class LLMProviderStore:
    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_providers(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/llm_providers"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"order": "priority.asc"},
            )
            _raise_for_status(resp, "list_llm_providers", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def count_models_by_provider(self) -> dict[str, int]:
        if not self.is_configured():
            return {}

        url = f"{self._rest_url()}/llm_models"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"select": "id,provider_id", "enabled": "eq.true"},
            )
            _raise_for_status(resp, "list_llm_models", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list):
                return {}

        counts: dict[str, int] = {}
        for row in rows:
            pid = str(row.get("provider_id") or "")
            counts[pid] = counts.get(pid, 0) + 1
        return counts


_store: LLMProviderStore | None = None


def get_llm_provider_store() -> LLMProviderStore:
    global _store
    if _store is None:
        _store = LLMProviderStore()
    return _store
