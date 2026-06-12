"""
Persistance Supabase — Monitoring Center (alertes, incidents, sources).
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

ALERT_SELECT = (
    "id,organization_id,alert_type,severity,title,message,source,source_id,"
    "status,acknowledged_at,resolved_at,created_at"
)

INCIDENT_SELECT = (
    "id,organization_id,title,description,severity,status,source,alert_id,"
    "detected_at,resolved_at,resolution_notes,created_at"
)

SOURCE_SELECT = "id,source_name,source_type,status,created_at"


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MonitoringStore:
    """CRUD PostgREST pour alerts, incidents et monitoring_sources."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_sources(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/monitoring_sources"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "select": SOURCE_SELECT,
                    "order": "source_name.asc",
                },
            )
            _raise_for_status(resp, "list_monitoring_sources", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        *,
        message: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        body: dict[str, Any] = {
            "organization_id": organization_id,
            "alert_type": alert_type.strip(),
            "severity": severity.strip(),
            "title": title.strip(),
            "status": "open",
        }
        if message:
            body["message"] = message
        if source:
            body["source"] = source.strip()
        if source_id:
            body["source_id"] = str(source_id).strip()

        url = f"{self._rest_url()}/alerts"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "create_alert", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[MonitoringStore] create_alert ignoré — %s", exc)
            return None

    async def list_alerts(
        self,
        *,
        status: str | None = "open",
        severity: str | None = None,
        alert_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": ALERT_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 200))),
        }
        if status:
            params["status"] = f"eq.{status.strip()}"
        if severity:
            params["severity"] = f"eq.{severity.strip()}"
        if alert_type:
            params["alert_type"] = f"eq.{alert_type.strip()}"

        url = f"{self._rest_url()}/alerts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_alerts", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def find_open_alert(self, alert_type: str) -> dict[str, Any] | None:
        rows = await self.list_alerts(
            status="open",
            alert_type=alert_type,
            limit=1,
        )
        if rows:
            return rows[0]
        rows = await self.list_alerts(
            status="acknowledged",
            alert_type=alert_type,
            limit=1,
        )
        return rows[0] if rows else None

    async def acknowledge_alert(self, alert_id: str) -> dict[str, Any] | None:
        return await self._patch_alert(
            alert_id,
            {"status": "acknowledged", "acknowledged_at": _now_iso()},
        )

    async def resolve_alert(self, alert_id: str) -> dict[str, Any] | None:
        return await self._patch_alert(
            alert_id,
            {"status": "resolved", "resolved_at": _now_iso()},
        )

    async def _patch_alert(
        self,
        alert_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not alert_id.strip():
            return None
        url = f"{self._rest_url()}/alerts"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"id": f"eq.{alert_id.strip()}"},
                    json=body,
                )
            _raise_for_status(resp, "patch_alert", "PATCH", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[MonitoringStore] patch_alert ignoré — %s", exc)
            return None

    async def create_incident(
        self,
        title: str,
        severity: str,
        *,
        description: str | None = None,
        source: str | None = None,
        alert_id: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        body: dict[str, Any] = {
            "organization_id": organization_id,
            "title": title.strip(),
            "severity": severity.strip(),
            "status": "open",
        }
        if description:
            body["description"] = description
        if source:
            body["source"] = source.strip()
        if alert_id:
            body["alert_id"] = alert_id.strip()

        url = f"{self._rest_url()}/incidents"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "create_incident", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[MonitoringStore] create_incident ignoré — %s", exc)
            return None

    async def list_incidents(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": INCIDENT_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 200))),
        }
        if status:
            params["status"] = f"eq.{status.strip()}"

        url = f"{self._rest_url()}/incidents"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_incidents", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def resolve_incident(
        self,
        incident_id: str,
        *,
        resolution_notes: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not incident_id.strip():
            return None

        body: dict[str, Any] = {
            "status": "resolved",
            "resolved_at": _now_iso(),
        }
        if resolution_notes:
            body["resolution_notes"] = resolution_notes.strip()

        url = f"{self._rest_url()}/incidents"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"id": f"eq.{incident_id.strip()}"},
                    json=body,
                )
            _raise_for_status(resp, "resolve_incident", "PATCH", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[MonitoringStore] resolve_incident ignoré — %s", exc)
            return None

    async def get_overview(self) -> dict[str, Any]:
        open_alerts = await self.list_alerts(status="open", limit=200)
        ack_alerts = await self.list_alerts(status="acknowledged", limit=200)
        open_incidents = await self.list_incidents(status="open", limit=200)
        sources = await self.list_sources()

        critical = sum(1 for a in open_alerts if str(a.get("severity")) == "critical")
        warning = sum(1 for a in open_alerts if str(a.get("severity")) == "warning")

        return {
            "open_alerts_count": len(open_alerts),
            "acknowledged_alerts_count": len(ack_alerts),
            "critical_alerts_count": critical,
            "warning_alerts_count": warning,
            "open_incidents_count": len(open_incidents),
            "sources_count": len(sources),
            "sources_active": sum(
                1 for s in sources if str(s.get("status") or "") == "active"
            ),
        }


_store: MonitoringStore | None = None


def get_monitoring_store() -> MonitoringStore:
    global _store
    if _store is None:
        _store = MonitoringStore()
    return _store


def reset_monitoring_store() -> None:
    global _store
    _store = None
