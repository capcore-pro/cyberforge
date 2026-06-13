"""
Routes API — Monitoring Center (health, alertes, incidents, checks).
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agents.alert_engine import run_checks
from api.routes.agents_status import get_agents_status
from api.routes.health import health_check
from config import get_settings
from db.llm_usage_store import get_llm_usage_store
from db.monitoring_store import get_monitoring_store
from db.supervisor_store import get_supervisor_store
from db.supabase_store import SupabaseStoreError
from security.llm_secrets import any_llm_key_configured

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


class ResolveIncidentBody(BaseModel):
    resolution_notes: str | None = None


def _compute_overall_status(
    *,
    critical_alerts: int,
    warning_alerts: int,
    open_incidents: int,
    pass_rate: float,
    total_validations: int,
    api_online: bool,
) -> str:
    if not api_online or critical_alerts > 0 or open_incidents > 0:
        return "critical"
    if (
        warning_alerts > 0
        or (total_validations > 0 and pass_rate < 0.9)
    ):
        return "degraded"
    return "healthy"


@router.get("/monitoring/health")
async def get_monitoring_health() -> dict:
    t0 = time.perf_counter()
    settings = get_settings()
    api_online = bool(settings.supabase_configured and any_llm_key_configured(settings))
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    health_t0 = time.perf_counter()
    await health_check()
    api_latency_ms = int((time.perf_counter() - health_t0) * 1000)

    agents_status = await get_agents_status()
    supervisor = await get_supervisor_store().get_supervisor_stats(days=30)

    llm_store = get_llm_usage_store()
    monthly = (
        await llm_store.get_dashboard_llm_stats()
        if llm_store.is_configured()
        else {"monthly": {"total_cost_usd": 0.0}, "daily": []}
    )
    daily = (
        await llm_store.get_daily_summary()
        if llm_store.is_configured()
        else {"total_cost_usd": 0.0}
    )

    store = get_monitoring_store()
    overview = (
        await store.get_overview()
        if store.is_configured()
        else {
            "critical_alerts_count": 0,
            "warning_alerts_count": 0,
            "open_incidents_count": 0,
        }
    )

    pass_rate = float(supervisor.get("pass_rate") or 0)
    total_validations = int(supervisor.get("total_validations") or 0)
    overall_status = _compute_overall_status(
        critical_alerts=int(overview.get("critical_alerts_count") or 0),
        warning_alerts=int(overview.get("warning_alerts_count") or 0),
        open_incidents=int(overview.get("open_incidents_count") or 0),
        pass_rate=pass_rate,
        total_validations=total_validations,
        api_online=api_online,
    )

    return {
        "overall_status": overall_status,
        "api_latency_ms": api_latency_ms,
        "api": {
            "status": "online" if api_online else "offline",
            "latency_ms": latency_ms,
        },
        "agents": {
            "active": agents_status.active_count,
            "total": agents_status.total_agents,
        },
        "pipeline": {
            "pass_rate": pass_rate,
            "avg_quality_score": float(supervisor.get("avg_quality_score") or 0),
            "days": int(supervisor.get("days") or 30),
        },
        "costs": {
            "today_usd": float(daily.get("total_cost_usd") or 0),
            "month_usd": float((monthly.get("monthly") or {}).get("total_cost_usd") or 0),
        },
    }


@router.get("/monitoring/overview")
async def get_monitoring_overview() -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        return {
            "open_alerts_count": 0,
            "acknowledged_alerts_count": 0,
            "critical_alerts_count": 0,
            "warning_alerts_count": 0,
            "open_incidents_count": 0,
            "sources_count": 0,
            "sources_active": 0,
        }
    try:
        return await store.get_overview()
    except SupabaseStoreError as exc:
        logger.warning("get_monitoring_overview: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/monitoring/sources")
async def list_monitoring_sources() -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_sources()
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_monitoring_sources: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/monitoring/alerts")
async def list_monitoring_alerts(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    status_filter = None if not status or status.strip().lower() == "all" else status
    try:
        items = await store.list_alerts(
            status=status_filter,
            severity=severity,
            limit=limit,
        )
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_monitoring_alerts: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_monitoring_alert(alert_id: str) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.acknowledge_alert(alert_id)
    except SupabaseStoreError as exc:
        logger.warning("acknowledge_monitoring_alert: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Alerte introuvable.")
    return row


@router.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_monitoring_alert(alert_id: str) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.resolve_alert(alert_id)
    except SupabaseStoreError as exc:
        logger.warning("resolve_monitoring_alert: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Alerte introuvable.")
    return row


@router.get("/monitoring/incidents")
async def list_monitoring_incidents(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_incidents(status=status, limit=limit)
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_monitoring_incidents: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/monitoring/incidents/{incident_id}/resolve")
async def resolve_monitoring_incident(
    incident_id: str,
    body: ResolveIncidentBody | None = None,
) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    notes = body.resolution_notes if body else None
    try:
        row = await store.resolve_incident(incident_id, resolution_notes=notes)
    except SupabaseStoreError as exc:
        logger.warning("resolve_monitoring_incident: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Incident introuvable.")
    return row


@router.post("/monitoring/check")
async def run_monitoring_check(days: int = Query(default=30, ge=1, le=365)) -> dict:
    try:
        return await run_checks(days=days)
    except SupabaseStoreError as exc:
        logger.warning("run_monitoring_check: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/monitoring/scan")
async def run_monitoring_scan(days: int = Query(default=30, ge=1, le=365)) -> dict:
    """Alias rétrocompat — préférer POST /monitoring/check."""
    return await run_monitoring_check(days=days)
