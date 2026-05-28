"""
Persistance Supabase — projets gérés par CyberForge (V1).

V1 cible : vitrines Next.js (une branche GitHub = un site) + déploiements Vercel.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
)

logger = logging.getLogger(__name__)

ProjectStatus = Literal["draft", "building", "deployed", "failed", "deleting", "deleted"]
RunAction = Literal["create", "update", "delete"]
RunStatus = Literal["running", "succeeded", "failed"]


class ManagedProjectRow(BaseModel):
    id: str
    type: str
    slug: str
    title: str | None = None
    prompt_original: str
    prompt_last: str
    status: str
    provider: str
    github_repo: str
    github_branch: str
    vercel_project_id: str | None = None
    vercel_frontend_project_id: str | None = None
    vercel_deployment_id_last: str | None = None
    url_preview: str | None = None
    url_production: str | None = None
    url_backend: str | None = None
    railway_project_id: str | None = None
    railway_service_id: str | None = None
    error_last: str | None = None
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class ManagedProjectRunRow(BaseModel):
    id: str
    project_id: str
    action: str
    status: str
    started_at: str
    finished_at: str | None = None
    error: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)


class ManagedProjectAuthRow(BaseModel):
    project_id: str
    enabled: bool = False
    client_email: str | None = None
    password_encrypted: str | None = None
    password_updated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ManagedProjectsStore:
    """
    Wrapper SupabaseStore spécialisé sur managed_projects / managed_project_runs.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._base = SupabaseStore(settings=settings)

    def is_configured(self) -> bool:
        return self._base.is_configured()

    def connection_diagnostics(self) -> dict[str, Any]:
        return self._base.connection_diagnostics()

    def _rest_url(self) -> str:
        return self._base._rest_url()  # noqa: SLF001

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        return self._base._headers(prefer)  # noqa: SLF001

    def to_http_detail(self, message: str) -> dict[str, Any]:
        diag = self.connection_diagnostics()
        return {
            "message": message,
            "operation": "managed_projects",
            "diagnostics": diag,
            "hint": "Vérifiez SUPABASE_* dans backend/.env puis redémarrez.",
        }

    async def create_project(
        self,
        *,
        type: str,
        slug: str,
        title: str | None,
        prompt: str,
        provider: str,
        github_repo: str,
        github_branch: str,
        vercel_project_id: str | None = None,
    ) -> ManagedProjectRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/managed_projects"
        payload = {
            "type": type,
            "slug": slug,
            "title": title,
            "prompt_original": prompt,
            "prompt_last": prompt,
            "status": "building",
            "provider": provider,
            "github_repo": github_repo,
            "github_branch": github_branch,
            "vercel_project_id": vercel_project_id,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._headers("return=representation"),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_managed_project", "POST", url, self._base)
            _raise_for_status(resp, "create_managed_project", "POST", url, self._base)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            return ManagedProjectRow(**row)

    async def update_project(
        self,
        project_id: str,
        *,
        patch: dict[str, Any],
    ) -> ManagedProjectRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/managed_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._headers("return=representation"),
                params={"id": f"eq.{project_id}"},
                json=patch,
            )
            _raise_for_status(resp, "update_managed_project", "PATCH", url, self._base)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            return ManagedProjectRow(**row)

    async def get_project(self, project_id: str) -> ManagedProjectRow | None:
        if not self.is_configured():
            return None

        url = f"{self._rest_url()}/managed_projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"id": f"eq.{project_id}", "select": "*"},
            )
            _raise_for_status(resp, "get_managed_project", "GET", url, self._base)
            rows = resp.json()
            if not rows:
                return None
            return ManagedProjectRow(**rows[0])

    async def list_projects(
        self,
        *,
        type: str | None = None,
        limit: int = 50,
    ) -> list[ManagedProjectRow]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/managed_projects"
        params: dict[str, str] = {
            "select": "*",
            "order": "updated_at.desc",
            "limit": str(limit),
            "deleted_at": "is.null",
        }
        if type:
            params["type"] = f"eq.{type}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            _raise_for_status(resp, "list_managed_projects", "GET", url, self._base)
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [ManagedProjectRow(**row) for row in data if isinstance(row, dict)]

    async def create_run(self, project_id: str, *, action: RunAction) -> ManagedProjectRunRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/managed_project_runs"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._headers("return=representation"),
                json={"project_id": project_id, "action": action, "status": "running"},
            )
            _raise_for_status(resp, "create_managed_run", "POST", url, self._base)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            return ManagedProjectRunRow(**row)

    async def finish_run(
        self,
        run_id: str,
        *,
        status: RunStatus,
        error: str | None = None,
        artifacts: dict[str, Any] | None = None,
    ) -> ManagedProjectRunRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/managed_project_runs"
        patch: dict[str, Any] = {
            "status": status,
            "finished_at": datetime.now(tz=UTC).isoformat(),
        }
        if error:
            patch["error"] = error
        if artifacts is not None:
            patch["artifacts"] = artifacts
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._headers("return=representation"),
                params={"id": f"eq.{run_id}"},
                json=patch,
            )
            _raise_for_status(resp, "finish_managed_run", "PATCH", url, self._base)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            return ManagedProjectRunRow(**row)

    async def list_runs(self, project_id: str, *, limit: int = 50) -> list[ManagedProjectRunRow]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/managed_project_runs"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={
                    "project_id": f"eq.{project_id}",
                    "select": "*",
                    "order": "started_at.desc",
                    "limit": str(limit),
                },
            )
            _raise_for_status(resp, "list_managed_runs", "GET", url, self._base)
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [ManagedProjectRunRow(**row) for row in data if isinstance(row, dict)]

    async def get_project_id_by_slug(self, *, slug: str, type: str = "vitrine_next") -> str | None:
        if not self.is_configured():
            return None
        cleaned = (slug or "").strip()
        if not cleaned:
            return None
        url = f"{self._rest_url()}/managed_projects"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"slug": f"eq.{cleaned}", "type": f"eq.{type}", "select": "id", "limit": "1"},
            )
            _raise_for_status(resp, "get_managed_project_id_by_slug", "GET", url, self._base)
            rows = resp.json()
            if not rows:
                return None
            row = rows[0]
            return str(row.get("id") or "").strip() or None

    async def get_project_auth(self, project_id: str) -> ManagedProjectAuthRow | None:
        if not self.is_configured():
            return None
        url = f"{self._rest_url()}/managed_project_auth"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={"project_id": f"eq.{project_id}", "select": "*"},
            )
            _raise_for_status(resp, "get_managed_project_auth", "GET", url, self._base)
            rows = resp.json()
            if not rows:
                return None
            return ManagedProjectAuthRow(**rows[0])

    async def upsert_project_auth(
        self,
        project_id: str,
        *,
        enabled: bool | None = None,
        client_email: str | None = None,
        password_encrypted: str | None = None,
        password_updated_at: str | None = None,
    ) -> ManagedProjectAuthRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        url = f"{self._rest_url()}/managed_project_auth"
        payload: dict[str, Any] = {"project_id": project_id}
        if enabled is not None:
            payload["enabled"] = bool(enabled)
        # Important: only patch client_email when explicitly provided, otherwise
        # password updates would wipe the stored email.
        if client_email is not None:
            payload["client_email"] = client_email
        if password_encrypted is not None:
            payload["password_encrypted"] = password_encrypted
        if password_updated_at is not None:
            payload["password_updated_at"] = password_updated_at
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._headers("resolution=merge-duplicates,return=representation"),
                json=payload,
            )
            _raise_for_status(resp, "upsert_managed_project_auth", "POST", url, self._base)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            return ManagedProjectAuthRow(**row)


_managed_store: ManagedProjectsStore | None = None


def get_managed_projects_store() -> ManagedProjectsStore:
    global _managed_store
    if _managed_store is None:
        _managed_store = ManagedProjectsStore(settings=get_settings())
    return _managed_store


def reset_managed_projects_store() -> None:
    global _managed_store
    _managed_store = None

