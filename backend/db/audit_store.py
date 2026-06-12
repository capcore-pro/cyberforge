"""
Persistance Supabase — audit logs (Volume 3).
"""

from __future__ import annotations

import logging
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


class AuditStore:
    """CRUD PostgREST pour audit_logs."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def log(
        self,
        event_type: str,
        *,
        actor_type: str = "system",
        actor_id: str | None = None,
        event_data: dict[str, Any] | None = None,
        project_id: str | None = None,
        ip_address: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            logger.warning("[AuditStore] Supabase non configuré — audit ignoré")
            return None

        body: dict[str, Any] = {
            "event_type": event_type.strip(),
            "actor_type": actor_type.strip(),
            "organization_id": organization_id,
        }
        if actor_id:
            body["actor_id"] = actor_id
        if event_data is not None:
            body["event_data"] = event_data
        if project_id:
            body["project_id"] = project_id
        if ip_address:
            body["ip_address"] = ip_address

        url = f"{self._rest_url()}/audit_logs"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    resp = await client.post(
                        url,
                        headers=self._supabase._headers("return=representation"),
                        json=body,
                    )
                except httpx.HTTPError as exc:
                    _raise_transport_error(exc, "audit_log", "POST", url, self._supabase)
                _raise_for_status(resp, "audit_log", "POST", url, self._supabase)
                return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[AuditStore] log ignoré — %s", exc)
            return None

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 500))),
        }
        if event_type:
            params["event_type"] = f"eq.{event_type.strip()}"
        if project_id:
            params["project_id"] = f"eq.{project_id.strip()}"

        url = f"{self._rest_url()}/audit_logs"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_audit_events", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []


_store: AuditStore | None = None


def get_audit_store() -> AuditStore:
    global _store
    if _store is None:
        _store = AuditStore()
    return _store


def reset_audit_store() -> None:
    global _store
    _store = None
