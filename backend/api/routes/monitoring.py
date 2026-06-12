"""
Routes API — Monitoring Center (alertes, incidents, scan).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agents.alert_engine import AlertEngine
from db.monitoring_store import get_monitoring_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


class ResolveIncidentBody(BaseModel):
    resolution_notes: str | None = None


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
    status: str | None = Query(default="open"),
    severity: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict:
    store = get_monitoring_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_alerts(
            status=status,
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


@router.post("/monitoring/scan")
async def run_monitoring_scan(days: int = Query(default=30, ge=1, le=365)) -> dict:
    try:
        return await AlertEngine(days=days).scan()
    except SupabaseStoreError as exc:
        logger.warning("run_monitoring_scan: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
