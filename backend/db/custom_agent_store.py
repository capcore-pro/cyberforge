"""
Persistance Supabase — Custom Agents (Agent Builder UI).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

CUSTOM_AGENT_SELECT = (
    "id,name,description,system_prompt,model,temperature,max_tokens,tools,"
    "is_active,created_at,updated_at"
)


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class CustomAgentStore:
    """CRUD PostgREST pour custom_agents."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_agents(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/custom_agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"select": CUSTOM_AGENT_SELECT, "order": "updated_at.desc"},
            )
            _raise_for_status(resp, "list_custom_agents", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        aid = (agent_id or "").strip()
        if not aid:
            return None
        url = f"{self._rest_url()}/custom_agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{aid}",
                    "select": CUSTOM_AGENT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_custom_agent", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def create_agent(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        payload = dict(body)
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/custom_agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_custom_agent", "POST", url, self._supabase)
            _raise_for_status(resp, "create_custom_agent", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création agent custom sans identifiant.")
            return row

    async def update_agent(self, agent_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        aid = (agent_id or "").strip()
        if not aid:
            return None
        payload = dict(patch)
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/custom_agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{aid}"},
                json=payload,
            )
            _raise_for_status(resp, "update_custom_agent", "PATCH", url, self._supabase)
            return _first_row(resp.json())

    async def delete_agent(self, agent_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        aid = (agent_id or "").strip()
        if not aid:
            return False
        url = f"{self._rest_url()}/custom_agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{aid}"},
            )
            _raise_for_status(resp, "delete_custom_agent", "DELETE", url, self._supabase)
        return True


_store: CustomAgentStore | None = None


def get_custom_agent_store() -> CustomAgentStore:
    global _store
    if _store is None:
        _store = CustomAgentStore()
    return _store


def reset_custom_agent_store() -> None:
    global _store
    _store = None

