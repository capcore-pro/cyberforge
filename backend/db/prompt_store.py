"""
Persistance Supabase — bibliothèque de prompts (Volume 3).
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

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _bump_patch_version(version: str) -> str:
    parts = (version or "1.0.0").strip().split(".")
    if len(parts) == 3 and parts[2].isdigit():
        parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
    return "1.0.1"


class PromptStore:
    """CRUD PostgREST pour prompts / prompt_versions."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def _resolve_category_id(self, category_slug: str) -> str | None:
        slug = (category_slug or "").strip()
        if not slug:
            return None
        url = f"{self._rest_url()}/prompt_categories"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"slug": f"eq.{slug}", "select": "id", "limit": "1"},
            )
            _raise_for_status(resp, "resolve_prompt_category", "GET", url, self._supabase)
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return str(rows[0].get("id") or "") or None
        return None

    async def create(
        self,
        name: str,
        slug: str,
        content: str,
        category_slug: str,
        *,
        agent_slug: str | None = None,
        description: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        category_id = await self._resolve_category_id(category_slug)
        body: dict[str, Any] = {
            "name": name.strip(),
            "slug": slug.strip(),
            "content": content,
            "status": "active",
            "version": "1.0.0",
            "organization_id": organization_id,
            "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
        }
        if category_id:
            body["category_id"] = category_id
        if agent_slug:
            body["agent_slug"] = agent_slug.strip()
        if description:
            body["description"] = description.strip()

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_prompt", "POST", url, self._supabase)
            _raise_for_status(resp, "create_prompt", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création prompt sans identifiant retourné.")
            return row

    async def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        if not self.is_configured() or not slug.strip():
            return None

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "slug": f"eq.{slug.strip()}",
                    "status": "eq.active",
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_prompt_by_slug", "GET", url, self._supabase)
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return rows[0]
        return None

    async def get_by_agent(self, agent_slug: str) -> list[dict[str, Any]]:
        if not self.is_configured() or not agent_slug.strip():
            return []

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "agent_slug": f"eq.{agent_slug.strip()}",
                    "status": "eq.active",
                    "order": "name.asc",
                },
            )
            _raise_for_status(resp, "get_prompts_by_agent", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def list_all(
        self,
        *,
        category_slug: str | None = None,
        status: str = "active",
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "order": "name.asc",
            "limit": "200",
        }
        if status:
            params["status"] = f"eq.{status.strip()}"
        if category_slug:
            category_id = await self._resolve_category_id(category_slug)
            if category_id:
                params["category_id"] = f"eq.{category_id}"

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_prompts", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def update_content(
        self,
        prompt_id: str,
        new_content: str,
        *,
        changelog: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{prompt_id}", "limit": "1"},
            )
            _raise_for_status(get_resp, "get_prompt_for_update", "GET", url, self._supabase)
            rows = get_resp.json()
            if not isinstance(rows, list) or not rows:
                raise SupabaseStoreError("Prompt introuvable.")
            current = rows[0]
            new_version = _bump_patch_version(str(current.get("version") or "1.0.0"))

            version_url = f"{self._rest_url()}/prompt_versions"
            ver_resp = await client.post(
                version_url,
                headers=self._supabase._headers("return=representation"),
                json={
                    "prompt_id": prompt_id,
                    "version": new_version,
                    "content": new_content,
                    "changelog": changelog,
                },
            )
            _raise_for_status(ver_resp, "create_prompt_version", "POST", version_url, self._supabase)

            patch_resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{prompt_id}"},
                json={
                    "content": new_content,
                    "version": new_version,
                    "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                },
            )
            _raise_for_status(patch_resp, "update_prompt_content", "PATCH", url, self._supabase)
            row = _first_row(patch_resp.json())
            if not row:
                raise SupabaseStoreError("Mise à jour prompt sans retour.")
            return row

    async def increment_usage(self, prompt_id: str) -> None:
        if not self.is_configured() or not prompt_id.strip():
            return

        url = f"{self._rest_url()}/prompts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{prompt_id}", "select": "usage_count", "limit": "1"},
            )
            _raise_for_status(get_resp, "get_prompt_usage", "GET", url, self._supabase)
            rows = get_resp.json()
            if not isinstance(rows, list) or not rows:
                return
            count = int(rows[0].get("usage_count") or 0) + 1
            await client.patch(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{prompt_id}"},
                json={"usage_count": count},
            )


_store: PromptStore | None = None


def get_prompt_store() -> PromptStore:
    global _store
    if _store is None:
        _store = PromptStore()
    return _store


def reset_prompt_store() -> None:
    global _store
    _store = None
