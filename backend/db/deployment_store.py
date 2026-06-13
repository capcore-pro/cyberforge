"""
Persistance Supabase — historique des déploiements (Volume 06A).
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

DEPLOYMENT_SELECT = (
    "id,project_id,generation_id,organization_id,deployment_name,"
    "deployment_type,provider,environment,status,url,duration_ms,"
    "error_message,deployed_at,created_at"
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


class DeploymentStore:
    """CRUD PostgREST pour la table deployments."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def record(
        self,
        *,
        project_id: str | None = None,
        generation_id: str | None = None,
        deployment_name: str | None = None,
        provider: str = "cloudflare",
        environment: str = "production",
        deployment_type: str = "application",
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "organization_id": DEFAULT_ORG_ID,
            "deployment_name": (deployment_name or "").strip() or None,
            "deployment_type": deployment_type.strip() or "application",
            "provider": provider.strip() or "cloudflare",
            "environment": environment.strip() or "production",
            "status": "pending",
            "created_at": _now_iso(),
        }
        if project_id and str(project_id).strip():
            body["project_id"] = str(project_id).strip()
        if generation_id and str(generation_id).strip():
            body["generation_id"] = str(generation_id).strip()

        url = f"{self._rest_url()}/deployments"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "record_deployment", "POST", url, self._supabase)
            _raise_for_status(resp, "record_deployment", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création deployment sans identifiant retourné.")
            return row

    async def update(
        self,
        deployment_id: str,
        *,
        status: str,
        url: str | None = None,
        duration_ms: int = 0,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "status": status.strip(),
            "duration_ms": max(0, int(duration_ms)),
        }
        if url is not None:
            body["url"] = url.strip() or None
        if error_message is not None:
            body["error_message"] = error_message
        if status.strip().lower() == "successful":
            body["deployed_at"] = _now_iso()

        patch_url = f"{self._rest_url()}/deployments"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.patch(
                    patch_url,
                    headers=self._supabase._headers("return=representation"),
                    params={"id": f"eq.{deployment_id.strip()}"},
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "update_deployment", "PATCH", patch_url, self._supabase)
            _raise_for_status(resp, "update_deployment", "PATCH", patch_url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError(
                    f"Déploiement '{deployment_id}' introuvable ou non mis à jour."
                )
            return row

    async def list_recent(
        self,
        *,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": DEPLOYMENT_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 100))),
        }
        if project_id and str(project_id).strip():
            params["project_id"] = f"eq.{project_id.strip()}"

        url = f"{self._rest_url()}/deployments"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_deployments", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def record_and_update(
        self,
        *,
        project_id: str | None = None,
        generation_id: str | None = None,
        deployment_name: str | None = None,
        url: str | None = None,
        duration_ms: int = 0,
        status: str = "successful",
        provider: str = "cloudflare",
        environment: str = "production",
        deployment_type: str = "application",
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        try:
            row = await self.record(
                project_id=project_id,
                generation_id=generation_id,
                deployment_name=deployment_name,
                provider=provider,
                environment=environment,
                deployment_type=deployment_type,
            )
            deployment_id = str(row.get("id") or "")
            if not deployment_id:
                return None
            return await self.update(
                deployment_id,
                status=status,
                url=url,
                duration_ms=duration_ms,
            )
        except SupabaseStoreError as exc:
            logger.warning("record_and_update deployment: %s", exc)
            return None


_store: DeploymentStore | None = None


def get_deployment_store() -> DeploymentStore:
    global _store
    if _store is None:
        _store = DeploymentStore()
    return _store


def reset_deployment_store() -> None:
    global _store
    _store = None
