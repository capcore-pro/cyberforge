"""
Persistance Supabase — Mobile Builder (mobile_apps, mobile_builds).
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

MOBILE_APP_SELECT = (
    "id,name,description,mode,sector,primary_color,secondary_color,logo_url,"
    "app_slug,bundle_id,features,screens,status,eas_build_id,apk_url,"
    "build_logs,created_at,updated_at"
)

MOBILE_BUILD_SELECT = (
    "id,app_id,build_number,eas_build_id,platform,status,apk_url,"
    "build_duration_ms,created_at"
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


class MobileAppStore:
    """CRUD PostgREST pour mobile_apps et mobile_builds."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_apps(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"select": MOBILE_APP_SELECT, "order": "updated_at.desc"},
            )
            _raise_for_status(resp, "list_mobile_apps", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_app(self, app_id: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        aid = (app_id or "").strip()
        if not aid:
            return None
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{aid}",
                    "select": MOBILE_APP_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_mobile_app", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def get_app_by_slug(self, app_slug: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        slug = (app_slug or "").strip()
        if not slug:
            return None
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "app_slug": f"eq.{slug}",
                    "select": MOBILE_APP_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_mobile_app_by_slug", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def create_app(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        payload = dict(body)
        if not payload.get("id"):
            payload["id"] = str(uuid4())
        payload.setdefault("features", [])
        payload.setdefault("screens", [])
        payload.setdefault("status", "draft")
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_mobile_app", "POST", url, self._supabase)
            _raise_for_status(resp, "create_mobile_app", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création app mobile sans identifiant.")
            return row

    async def update_app(self, app_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        aid = (app_id or "").strip()
        if not aid:
            return None
        payload = dict(patch)
        payload["updated_at"] = _now_iso()
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{aid}"},
                json=payload,
            )
            _raise_for_status(resp, "update_mobile_app", "PATCH", url, self._supabase)
            return _first_row(resp.json())

    async def delete_app(self, app_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        aid = (app_id or "").strip()
        if not aid:
            return False
        url = f"{self._rest_url()}/mobile_apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{aid}"},
            )
            _raise_for_status(resp, "delete_mobile_app", "DELETE", url, self._supabase)
        return True

    async def list_builds(self, app_id: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        aid = (app_id or "").strip()
        if not aid:
            return []
        url = f"{self._rest_url()}/mobile_builds"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "app_id": f"eq.{aid}",
                    "select": MOBILE_BUILD_SELECT,
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(resp, "list_mobile_builds", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_build(self, build_id: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        bid = (build_id or "").strip()
        if not bid:
            return None
        url = f"{self._rest_url()}/mobile_builds"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{bid}",
                    "select": MOBILE_BUILD_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_mobile_build", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def create_build(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        payload = dict(body)
        if not payload.get("id"):
            payload["id"] = str(uuid4())
        payload.setdefault("platform", "android")
        payload.setdefault("status", "pending")
        url = f"{self._rest_url()}/mobile_builds"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_mobile_build", "POST", url, self._supabase)
            _raise_for_status(resp, "create_mobile_build", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création build mobile sans identifiant.")
            return row

    async def update_build(self, build_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        bid = (build_id or "").strip()
        if not bid:
            return None
        url = f"{self._rest_url()}/mobile_builds"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{bid}"},
                json=patch,
            )
            _raise_for_status(resp, "update_mobile_build", "PATCH", url, self._supabase)
            return _first_row(resp.json())

    async def next_build_number(self, app_id: str) -> int:
        builds = await self.list_builds(app_id)
        if not builds:
            return 1
        numbers = [int(b.get("build_number") or 0) for b in builds]
        return max(numbers) + 1


_store: MobileAppStore | None = None


def get_mobile_app_store() -> MobileAppStore:
    global _store
    if _store is None:
        _store = MobileAppStore()
    return _store


def reset_mobile_app_store() -> None:
    global _store
    _store = None
