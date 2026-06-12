"""
Persistance Supabase — exécutions agents (Volume 3).
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

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _agent_slug(agent_name: str) -> str:
    return (agent_name or "").strip().lower().replace(" ", "_")


class AgentExecutionStore:
    """CRUD PostgREST pour agent_executions."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def record(
        self,
        agent_name: str,
        execution_type: str = "generation",
        status: str = "pending",
        *,
        project_id: str | None = None,
        generation_id: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        execution_cost: float = 0,
        duration_ms: int = 0,
        error_message: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        inp = max(0, int(input_tokens or 0))
        out = max(0, int(output_tokens or 0))
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        body: dict[str, Any] = {
            "agent_name": agent_name.strip(),
            "agent_slug": _agent_slug(agent_name),
            "execution_type": (execution_type or "generation").strip(),
            "status": (status or "pending").strip(),
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": inp + out,
            "execution_cost": float(execution_cost or 0),
            "duration_ms": max(0, int(duration_ms or 0)),
            "started_at": now,
            "organization_id": organization_id,
        }
        if project_id:
            body["project_id"] = project_id
        if generation_id:
            body["generation_id"] = generation_id
        if error_message:
            body["error_message"] = error_message
        if status in ("success", "failed", "error"):
            body["finished_at"] = now

        url = f"{self._rest_url()}/agent_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "record_agent_execution", "POST", url, self._supabase)
            _raise_for_status(resp, "record_agent_execution", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création agent_execution sans identifiant retourné.")
            return row

    async def update_status(
        self,
        execution_id: str,
        status: str,
        *,
        finished_at: datetime | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        patch: dict[str, Any] = {"status": status.strip()}
        if finished_at is not None:
            patch["finished_at"] = finished_at.replace(tzinfo=None).isoformat()
        elif status in ("success", "failed", "error"):
            patch["finished_at"] = datetime.now(UTC).replace(tzinfo=None).isoformat()
        if error_message is not None:
            patch["error_message"] = error_message

        url = f"{self._rest_url()}/agent_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{execution_id}"},
                json=patch,
            )
            _raise_for_status(resp, "update_agent_execution", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Mise à jour agent_execution sans retour.")
            return row

    async def list_by_project(self, project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.is_configured() or not project_id.strip():
            return []

        url = f"{self._rest_url()}/agent_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "project_id": f"eq.{project_id}",
                    "order": "created_at.desc",
                    "limit": str(max(1, min(limit, 200))),
                },
            )
            _raise_for_status(resp, "list_agent_executions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(
        self,
        *,
        agent_name: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_duration_ms": 0,
                "total_cost": 0.0,
            }

        since = (datetime.now(UTC) - timedelta(days=max(1, days))).replace(tzinfo=None)
        params: dict[str, str] = {
            "created_at": f"gte.{since.isoformat()}",
            "select": "status,duration_ms,execution_cost",
            "limit": "1000",
        }
        if agent_name:
            params["agent_name"] = f"eq.{agent_name.strip()}"

        url = f"{self._rest_url()}/agent_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "agent_execution_stats", "GET", url, self._supabase)
            rows = resp.json() if isinstance(resp.json(), list) else []

        total = len(rows)
        success = sum(1 for r in rows if str(r.get("status") or "").lower() == "success")
        failure = sum(
            1
            for r in rows
            if str(r.get("status") or "").lower() in ("failed", "error")
        )
        durations = [int(r.get("duration_ms") or 0) for r in rows if r.get("duration_ms")]
        costs = [float(r.get("execution_cost") or 0) for r in rows]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0
        return {
            "total_executions": total,
            "success_count": success,
            "failure_count": failure,
            "avg_duration_ms": avg_duration,
            "total_cost": round(sum(costs), 6),
        }


_store: AgentExecutionStore | None = None


def get_agent_execution_store() -> AgentExecutionStore:
    global _store
    if _store is None:
        _store = AgentExecutionStore()
    return _store


def reset_agent_execution_store() -> None:
    global _store
    _store = None
