"""
Persistance Supabase — Workflow Engine (définitions, étapes, exécutions).
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

WORKFLOW_SELECT = (
    "id,workflow_id,name,description,workflow_type,project_types,"
    "version,status,created_at,updated_at"
)

STEP_SELECT = (
    "id,workflow_id,step_name,step_type,agent_id,tool_id,"
    "execution_order,is_optional,condition_field,condition_values,created_at"
)

EXECUTION_SELECT = (
    "id,workflow_id,generation_id,project_id,organization_id,status,"
    "current_step,total_steps,completed_steps,total_cost_usd,total_tokens,"
    "duration_ms,error_message,started_at,completed_at,created_at"
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


def _project_types_contains(project_types: object, project_type: str) -> bool:
    needle = (project_type or "").strip().lower()
    if not needle:
        return False
    if isinstance(project_types, list):
        return any(str(item).strip().lower() == needle for item in project_types)
    return False


class WorkflowStore:
    """CRUD PostgREST pour workflows / workflow_steps / workflow_executions."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_workflows(self, *, status: str = "active") -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": WORKFLOW_SELECT,
            "order": "name.asc",
        }
        if status:
            params["status"] = f"eq.{status.strip()}"

        url = f"{self._rest_url()}/workflows"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_workflows", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not workflow_id.strip():
            return None

        url = f"{self._rest_url()}/workflows"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "workflow_id": f"eq.{workflow_id.strip()}",
                    "select": WORKFLOW_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_workflow", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def get_steps(self, workflow_uuid: str) -> list[dict[str, Any]]:
        if not self.is_configured() or not workflow_uuid.strip():
            return []

        url = f"{self._rest_url()}/workflow_steps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "workflow_id": f"eq.{workflow_uuid.strip()}",
                    "select": STEP_SELECT,
                    "order": "execution_order.asc",
                },
            )
            _raise_for_status(resp, "get_workflow_steps", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_workflow_for_project_type(self, project_type: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        needle = (project_type or "").strip().lower()
        if not needle:
            return None

        workflows = await self.list_workflows(status="active")
        for workflow in workflows:
            if _project_types_contains(workflow.get("project_types"), needle):
                return workflow
        return None

    async def create_execution(
        self,
        workflow_uuid: str,
        generation_id: str,
        *,
        project_id: str | None = None,
        total_steps: int = 0,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        now = _now_iso()
        body: dict[str, Any] = {
            "workflow_id": workflow_uuid.strip(),
            "generation_id": generation_id.strip(),
            "organization_id": DEFAULT_ORG_ID,
            "status": "running",
            "total_steps": max(0, int(total_steps)),
            "completed_steps": 0,
            "started_at": now,
        }
        if project_id:
            body["project_id"] = str(project_id).strip()

        url = f"{self._rest_url()}/workflow_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_execution", "POST", url, self._supabase)
            _raise_for_status(resp, "create_execution", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Exécution workflow sans identifiant retourné.")
            return row

    async def update_execution(
        self,
        execution_id: str,
        *,
        current_step: str | None = None,
        completed_steps: int | None = None,
        status: str | None = None,
        total_cost_usd: float | None = None,
        total_tokens: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {}
        if current_step is not None:
            body["current_step"] = current_step.strip()
        if completed_steps is not None:
            body["completed_steps"] = max(0, int(completed_steps))
        if status is not None:
            body["status"] = status.strip()
        if total_cost_usd is not None:
            body["total_cost_usd"] = float(total_cost_usd)
        if total_tokens is not None:
            body["total_tokens"] = int(total_tokens)
        if duration_ms is not None:
            body["duration_ms"] = int(duration_ms)
        if error_message is not None:
            body["error_message"] = error_message

        if not body:
            raise SupabaseStoreError("update_execution sans champs à mettre à jour.")

        url = f"{self._rest_url()}/workflow_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"id": f"eq.{execution_id.strip()}"},
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "update_execution", "PATCH", url, self._supabase)
            _raise_for_status(resp, "update_execution", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError(f"Exécution '{execution_id}' introuvable ou non mise à jour.")
            return row

    async def complete_execution(
        self,
        execution_id: str,
        status: str,
        *,
        total_cost_usd: float = 0,
        total_tokens: int = 0,
        duration_ms: int = 0,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "status": status.strip(),
            "total_cost_usd": float(total_cost_usd),
            "total_tokens": int(total_tokens),
            "duration_ms": int(duration_ms),
            "completed_at": _now_iso(),
        }
        if error_message is not None:
            body["error_message"] = error_message

        url = f"{self._rest_url()}/workflow_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"id": f"eq.{execution_id.strip()}"},
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "complete_execution", "PATCH", url, self._supabase)
            _raise_for_status(resp, "complete_execution", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError(f"Exécution '{execution_id}' introuvable.")
            return row

    async def get_execution(self, generation_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not generation_id.strip():
            return None

        url = f"{self._rest_url()}/workflow_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "generation_id": f"eq.{generation_id.strip()}",
                    "select": EXECUTION_SELECT,
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_execution", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def list_executions(
        self,
        *,
        workflow_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": EXECUTION_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 100))),
        }
        if workflow_id:
            workflow = await self.get_workflow(workflow_id)
            if workflow and workflow.get("id"):
                params["workflow_id"] = f"eq.{workflow['id']}"
            else:
                return []
        if project_id:
            params["project_id"] = f"eq.{project_id.strip()}"
        if status:
            params["status"] = f"eq.{status.strip()}"

        url = f"{self._rest_url()}/workflow_executions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_executions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []


_store: WorkflowStore | None = None


def get_workflow_store() -> WorkflowStore:
    global _store
    if _store is None:
        _store = WorkflowStore()
    return _store


def reset_workflow_store() -> None:
    global _store
    _store = None
