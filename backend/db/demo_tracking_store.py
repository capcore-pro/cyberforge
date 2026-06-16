"""
Persistance Supabase — demo_views (tracker vues démos).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

DeviceType = Literal["mobile", "tablet", "desktop"]


def detect_device_type(user_agent: str | None) -> DeviceType:
    """Détecte le type d'appareil depuis le User-Agent."""
    ua = (user_agent or "").lower()
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    return "desktop"


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


class DemoTrackingStore:
    """CRUD PostgREST pour demo_views."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def record_view(
        self,
        project_id: str,
        demo_url: str,
        *,
        visitor_ip: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        pid = project_id.strip()
        url = demo_url.strip()
        if not pid or not url:
            raise SupabaseStoreError("project_id et demo_url requis.")

        ip = (visitor_ip or "").strip()[:45] or None
        ua = (user_agent or "").strip() or None
        ref = (referer or "").strip() or None
        device_type = detect_device_type(ua)

        body: dict[str, Any] = {
            "project_id": pid,
            "demo_url": url,
            "device_type": device_type,
        }
        if ip:
            body["visitor_ip"] = ip
        if ua:
            body["user_agent"] = ua[:4000]
        if ref:
            body["referer"] = ref[:2000]

        endpoint = f"{self._rest_url()}/demo_views"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    endpoint,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "record_demo_view", "POST", endpoint, self._supabase)
            _raise_for_status(resp, "record_demo_view", "POST", endpoint, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Enregistrement vue démo sans réponse.")
            return row

    async def list_views(
        self,
        project_id: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        pid = project_id.strip()
        if not pid:
            return []
        url = f"{self._rest_url()}/demo_views"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "project_id": f"eq.{pid}",
                    "order": "created_at.desc",
                    "limit": str(max(1, min(limit, 500))),
                },
            )
            _raise_for_status(resp, "list_demo_views", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(self, project_id: str) -> dict[str, Any]:
        views = await self.list_views(project_id, limit=500)
        now = datetime.now(UTC)
        week_start = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        by_device: dict[str, int] = {"mobile": 0, "tablet": 0, "desktop": 0}
        unique_ips: set[str] = set()
        last_viewed_at: str | None = None
        views_this_week = 0
        views_this_month = 0

        for row in views:
            device = str(row.get("device_type") or "desktop").lower()
            if device in by_device:
                by_device[device] += 1
            else:
                by_device["desktop"] += 1

            ip = str(row.get("visitor_ip") or "").strip()
            if ip:
                unique_ips.add(ip)

            created_raw = row.get("created_at")
            if last_viewed_at is None and created_raw:
                last_viewed_at = str(created_raw)

            created = _parse_created_at(str(created_raw) if created_raw else None)
            if created:
                if created >= week_start:
                    views_this_week += 1
                if created >= month_start:
                    views_this_month += 1

        return {
            "total_views": len(views),
            "unique_ips": len(unique_ips),
            "by_device": by_device,
            "last_viewed_at": last_viewed_at,
            "views_this_week": views_this_week,
            "views_this_month": views_this_month,
        }


_store: DemoTrackingStore | None = None


def get_demo_tracking_store() -> DemoTrackingStore:
    global _store
    if _store is None:
        _store = DemoTrackingStore()
    return _store


def reset_demo_tracking_store() -> None:
    global _store
    _store = None
