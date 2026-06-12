"""
Persistance Supabase — Agent Registry (registre officiel des agents IA).
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

AGENT_SELECT = (
    "id,agent_id,name,slug,category,description,version,provider,model,"
    "capabilities,system_prompt_slug,enabled,in_pipeline,requires_key,"
    "created_at,updated_at"
)


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


class AgentRegistryStore:
    """CRUD PostgREST pour la table agents."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_all(
        self,
        *,
        enabled: bool | None = None,
        in_pipeline: bool | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": AGENT_SELECT,
            "order": "category.asc,name.asc",
        }
        if enabled is not None:
            params["enabled"] = f"eq.{str(enabled).lower()}"
        if in_pipeline is not None:
            params["in_pipeline"] = f"eq.{str(in_pipeline).lower()}"
        if category:
            params["category"] = f"eq.{category.strip()}"

        url = f"{self._rest_url()}/agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_agents", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_by_agent_id(self, agent_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not agent_id.strip():
            return None

        url = f"{self._rest_url()}/agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "agent_id": f"eq.{agent_id.strip()}",
                    "select": AGENT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_agent_by_id", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        if not self.is_configured() or not slug.strip():
            return None

        url = f"{self._rest_url()}/agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "slug": f"eq.{slug.strip()}",
                    "select": AGENT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_agent_by_slug", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def _patch_by_agent_id(self, agent_id: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        patch_body = {**body, "updated_at": _now_iso()}
        url = f"{self._rest_url()}/agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"agent_id": f"eq.{agent_id.strip()}"},
                    json=patch_body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "patch_agent", "PATCH", url, self._supabase)
            _raise_for_status(resp, "patch_agent", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError(f"Agent '{agent_id}' introuvable ou non mis à jour.")
            return row

    async def update_version(self, agent_id: str, version: str) -> dict[str, Any]:
        return await self._patch_by_agent_id(agent_id, {"version": version.strip()})

    async def update_model(self, agent_id: str, model: str, provider: str) -> dict[str, Any]:
        return await self._patch_by_agent_id(
            agent_id,
            {"model": model.strip(), "provider": provider.strip()},
        )

    async def set_enabled(self, agent_id: str, enabled: bool) -> dict[str, Any]:
        return await self._patch_by_agent_id(agent_id, {"enabled": enabled})

    async def get_pipeline_agents(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/agents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "in_pipeline": "eq.true",
                    "select": AGENT_SELECT,
                    "order": "name.asc",
                },
            )
            _raise_for_status(resp, "get_pipeline_agents", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []


_store: AgentRegistryStore | None = None


def get_agent_registry_store() -> AgentRegistryStore:
    global _store
    if _store is None:
        _store = AgentRegistryStore()
    return _store


def reset_agent_registry_store() -> None:
    global _store
    _store = None
