"""
Persistance Supabase — ERP Builder (erp_projects).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

ERP_PROJECT_SELECT = (
    "id,name,client_name,erp_type,company_size,budget,modules,primary_color,"
    "logo_url,domain,admin_email,admin_password,docker_compose_content,"
    "container_name,port,status,url,install_logs,created_at,updated_at"
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


class ErpStore:
    """CRUD PostgREST pour erp_projects."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_projects(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/erp_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"select": ERP_PROJECT_SELECT, "order": "updated_at.desc"},
            )
            _raise_for_status(resp, "list_erp_projects", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        pid = (project_id or "").strip()
        if not pid:
            return None
        url = f"{self._rest_url()}/erp_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{pid}",
                    "select": ERP_PROJECT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_erp_project", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def create_project(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        payload = dict(body)
        if not payload.get("id"):
            payload["id"] = str(uuid4())
        payload.setdefault("modules", [])
        payload.setdefault("status", "draft")
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/erp_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_erp_project", "POST", url, self._supabase)
            _raise_for_status(resp, "create_erp_project", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création projet ERP sans identifiant.")
            return row

    async def update_project(self, project_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        pid = (project_id or "").strip()
        if not pid:
            return None
        payload = dict(patch)
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/erp_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{pid}"},
                json=payload,
            )
            _raise_for_status(resp, "update_erp_project", "PATCH", url, self._supabase)
            return _first_row(resp.json())

    async def delete_project(self, project_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        pid = (project_id or "").strip()
        if not pid:
            return False
        url = f"{self._rest_url()}/erp_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{pid}"},
            )
            _raise_for_status(resp, "delete_erp_project", "DELETE", url, self._supabase)
        return True

    async def count_projects(self) -> int:
        rows = await self.list_projects()
        return len(rows)


_store: ErpStore | None = None


def get_erp_store() -> ErpStore:
    global _store
    if _store is None:
        _store = ErpStore()
    return _store


def reset_erp_store() -> None:
    global _store
    _store = None
