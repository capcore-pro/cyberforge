"""
Persistance Supabase — Tool Framework (registre, exécutions, audit).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
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

TOOL_SELECT = (
    "id,tool_id,name,slug,category,description,version,requires_key,"
    "enabled,created_at,updated_at"
)

EXECUTION_SELECT = (
    "id,tool_id,agent_id,project_id,generation_id,action,status,"
    "duration_ms,error_message,metadata,created_at"
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


class ToolStore:
    """CRUD PostgREST pour tool_registry / tool_executions / tool_audit_logs."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_tools(
        self,
        *,
        enabled: bool | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": TOOL_SELECT,
            "order": "category.asc,name.asc",
        }
        if enabled is not None:
            params["enabled"] = f"eq.{str(enabled).lower()}"
        if category:
            params["category"] = f"eq.{category.strip()}"

        url = f"{self._rest_url()}/tool_registry"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_tools", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_tool(self, tool_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not tool_id.strip():
            return None

        url = f"{self._rest_url()}/tool_registry"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "tool_id": f"eq.{tool_id.strip()}",
                    "select": TOOL_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_tool", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def record_execution(
        self,
        tool_id: str,
        action: str,
        status: str,
        *,
        agent_id: str | None = None,
        project_id: str | None = None,
        generation_id: str | None = None,
        duration_ms: int = 0,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "tool_id": tool_id.strip(),
            "action": action.strip(),
            "status": status.strip(),
            "duration_ms": max(0, int(duration_ms)),
        }
        if agent_id:
            body["agent_id"] = agent_id.strip()
        if project_id:
            body["project_id"] = project_id.strip()
        if generation_id:
            body["generation_id"] = generation_id.strip()
        if error_message:
            body["error_message"] = error_message
        if metadata is not None:
            body["metadata"] = metadata

        url = f"{self._rest_url()}/tool_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "record_execution", "POST", url, self._supabase)
            _raise_for_status(resp, "record_execution", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Exécution outil sans identifiant retourné.")
            return row

    async def list_executions(
        self,
        *,
        tool_id: str | None = None,
        days: int = 30,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        since = (datetime.now(UTC) - timedelta(days=max(1, days))).replace(tzinfo=None)
        params: dict[str, str] = {
            "select": EXECUTION_SELECT,
            "created_at": f"gte.{since.isoformat()}",
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 1000))),
        }
        if tool_id:
            params["tool_id"] = f"eq.{tool_id.strip()}"

        url = f"{self._rest_url()}/tool_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_executions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(
        self,
        tool_id: str | None = None,
        *,
        days: int = 30,
    ) -> dict[str, Any]:
        rows = await self.list_executions(tool_id=tool_id, days=days)
        total = len(rows)
        success_count = sum(1 for r in rows if r.get("status") == "success")
        failure_count = sum(1 for r in rows if r.get("status") == "failure")
        durations = [
            int(r.get("duration_ms") or 0)
            for r in rows
            if int(r.get("duration_ms") or 0) > 0
        ]
        avg_duration_ms = int(sum(durations) / len(durations)) if durations else 0
        return {
            "tool_id": tool_id,
            "days": days,
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "avg_duration_ms": avg_duration_ms,
        }

    async def audit_log(
        self,
        tool_id: str,
        action: str,
        result: str,
        *,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "tool_id": tool_id.strip(),
            "action": action.strip(),
            "result": result.strip(),
        }
        if agent_id:
            body["agent_id"] = agent_id.strip()
        if metadata is not None:
            body["metadata"] = metadata

        url = f"{self._rest_url()}/tool_audit_logs"
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
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Audit outil sans identifiant retourné.")
            return row


_store: ToolStore | None = None


def get_tool_store() -> ToolStore:
    global _store
    if _store is None:
        _store = ToolStore()
    return _store


def reset_tool_store() -> None:
    global _store
    _store = None
