"""
Persistance Supabase — Security events (Volume 7).
"""

from __future__ import annotations

import logging
from collections import Counter
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

EVENT_SELECT = (
    "id,organization_id,event_type,severity,source,actor_type,actor_id,"
    "description,metadata,resolved,created_at"
)

SEVERITIES = ("low", "medium", "high", "critical")


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


class SecurityStore:
    """CRUD PostgREST pour security_events."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def log_event(
        self,
        event_type: str,
        severity: str = "low",
        source: str | None = None,
        actor_type: str = "user",
        actor_id: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            logger.warning("SecurityStore.log_event ignoré — Supabase non configuré.")
            return {}

        body: dict[str, Any] = {
            "organization_id": DEFAULT_ORG_ID,
            "event_type": event_type.strip(),
            "severity": (severity or "low").strip(),
            "actor_type": (actor_type or "user").strip(),
            "metadata": metadata or {},
        }
        if source:
            body["source"] = source.strip()
        if actor_id:
            body["actor_id"] = str(actor_id).strip()
        if description:
            body["description"] = description.strip()

        url = f"{self._rest_url()}/security_events"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "log_security_event", "POST", url)
            _raise_for_status(resp, "log_security_event", "POST", url, self._supabase)
            return _first_row(resp.json()) or {}

    async def list_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": EVENT_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 500))),
        }
        if event_type:
            params["event_type"] = f"eq.{event_type.strip()}"
        if severity:
            params["severity"] = f"eq.{severity.strip()}"

        url = f"{self._rest_url()}/security_events"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    url, headers=self._supabase._headers(), params=params
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "list_security_events", "GET", url)
            _raise_for_status(resp, "list_security_events", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "total": 0,
                "by_severity": {s: 0 for s in SEVERITIES},
                "by_type": {},
                "unresolved": 0,
            }

        url = f"{self._rest_url()}/security_events"
        params = {
            "select": "event_type,severity,resolved",
            "limit": "1000",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    url, headers=self._supabase._headers(), params=params
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "security_stats", "GET", url)
            _raise_for_status(resp, "security_stats", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list):
                rows = []

        by_severity: Counter[str] = Counter()
        by_type: Counter[str] = Counter()
        unresolved = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            sev = str(row.get("severity") or "low")
            by_severity[sev] += 1
            evt = str(row.get("event_type") or "unknown")
            by_type[evt] += 1
            if not row.get("resolved"):
                unresolved += 1

        return {
            "total": len(rows),
            "by_severity": {s: by_severity.get(s, 0) for s in SEVERITIES},
            "by_type": dict(by_type),
            "unresolved": unresolved,
        }


_security_store: SecurityStore | None = None


def get_security_store() -> SecurityStore:
    global _security_store
    if _security_store is None:
        _security_store = SecurityStore()
    return _security_store


def reset_security_store() -> None:
    global _security_store
    _security_store = None
