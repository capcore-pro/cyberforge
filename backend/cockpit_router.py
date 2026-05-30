"""
API cockpit financier — services, soldes, sync, alertes, dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import cockpit_db as db
from config import get_settings
from cockpit_connectors import get_connector
from cockpit_connectors.manual import ManualConnector
from cockpit_sync import evaluate_threshold_alerts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cockpit"])

_sync_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="cockpit-sync")


# --- Schémas ---


class ServiceCreateBody(BaseModel):
    name: str = Field(min_length=1)
    api_key_env: str = Field(min_length=1)
    connector: str | None = None
    color: str | None = None
    icon: str | None = None
    currency: str = "EUR"
    enabled: bool = True


class ServiceUpdateBody(BaseModel):
    name: str | None = None
    api_key_env: str | None = None
    connector: str | None = None
    color: str | None = None
    icon: str | None = None
    currency: str | None = None
    enabled: bool | None = None


class TopupBody(BaseModel):
    amount_eur: float = Field(gt=0, description="Montant de recharge strictement positif")
    description: str | None = None


class ThresholdsBody(BaseModel):
    warning_eur: float | None = Field(default=None, ge=0)
    critical_eur: float | None = Field(default=None, ge=0)
    urgent_eur: float | None = Field(default=None, ge=0)


class MarkAlertsReadBody(BaseModel):
    alert_ids: list[str] | None = None


# --- Helpers ---


def _normalize_service(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if "enabled" in out:
        out["enabled"] = bool(out["enabled"])
    if "read" in out:
        out["read"] = bool(out["read"])
    return out


def _api_key_for_service(service: dict[str, Any]) -> str:
    from security.llm_secrets import get_effective_llm_key
    from security.secret_encoding import read_env_secret, secret_for_http_header
    from security.secret_vault import get_secret_vault

    env_name = (service.get("api_key_env") or "").strip()
    if not env_name:
        return ""

    if env_name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
    ):
        settings = get_settings()
        llm = get_effective_llm_key(env_name, settings)
        if llm:
            return secret_for_http_header(llm)

    vault_val = get_secret_vault().peek(env_name)
    if vault_val:
        return secret_for_http_header(vault_val)
    return secret_for_http_header(read_env_secret(env_name))


def _resolve_connector(service: dict[str, Any]):
    service_id = str(service["id"])
    connector_name = (service.get("connector") or service_id).strip()
    api_key = _api_key_for_service(service)
    conn = get_connector(connector_name, api_key, service_id=service_id)
    if conn is None:
        conn = ManualConnector(service_id=service_id, api_key=api_key)
    return conn


def _ping_service(service: dict[str, Any]) -> bool:
    try:
        return bool(_resolve_connector(service).ping())
    except Exception:
        logger.debug("Ping échoué pour %s", service.get("id"), exc_info=True)
        return False


def _service_payload(service: dict[str, Any], *, ping: bool | None = None) -> dict[str, Any]:
    sid = str(service["id"])
    balance = db.get_balance(sid)
    thresholds = db.get_thresholds(sid)
    ping_ok = _ping_service(service) if ping is None else ping
    return {
        **_normalize_service(service),
        "balance": balance,
        "thresholds": thresholds,
        "ping_ok": ping_ok,
    }


def _sync_service_blocking(service_id: str) -> dict[str, Any]:
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service introuvable.")

    conn = _resolve_connector(service)
    try:
        balance = float(conn.get_balance())
    except Exception as exc:
        logger.warning("Sync balance %s : %s", service_id, exc)
        row = db.get_balance(service_id)
        balance = float(row.get("balance_eur") or 0) if row else 0.0

    updated = db.set_balance(service_id, balance)
    alerts = [
        _normalize_service(a)
        for a in evaluate_threshold_alerts(
            service_id,
            balance,
            service_name=str(service.get("name") or service_id),
        )
    ]
    return {
        "service_id": service_id,
        "balance": updated,
        "balance_eur": balance,
        "alerts_created": alerts,
    }


async def _run_sync(service_id: str) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_sync_pool, _sync_service_blocking, service_id)


async def _notify_low_balance_from_sync(result: dict[str, Any]) -> None:
    alerts = result.get("alerts_created") or []
    if not alerts:
        return

    from routers.notifications import notify

    service_id = str(result.get("service_id") or "")
    service = db.get_service(service_id) if service_id else None
    service_name = str(
        (service or {}).get("name") or service_id or "Service API"
    )
    balance = float(result.get("balance_eur") or 0)
    balance_label = f"{balance:.2f} €" if balance != int(balance) else f"{int(balance)} €"

    try:
        await notify(
            "Solde API bas ⚠️",
            "api_balance_low",
            "warning",
            f"{service_name} : {balance_label} restant",
        )
    except Exception as exc:
        logger.warning("Notification solde API ignorée : %s", exc)


def _require_service(service_id: str) -> dict[str, Any]:
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service introuvable.")
    return service


# --- Services ---


@router.get("/services")
async def list_services() -> list[dict[str, Any]]:
    services = db.get_all_services()
    loop = asyncio.get_running_loop()
    pings = await asyncio.gather(
        *[
            loop.run_in_executor(_sync_pool, _ping_service, svc)
            for svc in services
        ]
    )
    return [
        _service_payload(svc, ping=ping_ok)
        for svc, ping_ok in zip(services, pings)
    ]


@router.post("/services", status_code=201)
async def create_service(body: ServiceCreateBody) -> dict[str, Any]:
    try:
        sid = db.add_service(
            name=body.name,
            api_key_env=body.api_key_env,
            connector=body.connector,
            color=body.color,
            icon=body.icon,
            currency=body.currency,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = db.get_service(sid)
    assert service is not None
    return _service_payload(service)


@router.put("/services/{service_id}")
async def update_service(service_id: str, body: ServiceUpdateBody) -> dict[str, Any]:
    _require_service(service_id)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return _service_payload(_require_service(service_id))

    updated = db.update_service(service_id, **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="Service introuvable.")
    return _service_payload(updated)


@router.delete("/services/{service_id}")
async def remove_service(service_id: str) -> dict[str, str]:
    if not db.delete_service(service_id):
        raise HTTPException(status_code=404, detail="Service introuvable.")
    return {"status": "deleted", "service_id": service_id}


# --- Balances & sync ---


@router.get("/balances")
async def list_balances() -> list[dict[str, Any]]:
    return db.get_all_balances()


@router.post("/services/{service_id}/sync")
async def sync_service(service_id: str) -> dict[str, Any]:
    result = await _run_sync(service_id)
    await _notify_low_balance_from_sync(result)
    return result


@router.post("/sync-all")
async def sync_all_enabled() -> dict[str, Any]:
    services = db.get_all_services(enabled_only=True)
    results = await asyncio.gather(
        *[_run_sync(str(s["id"])) for s in services],
        return_exceptions=True,
    )
    synced: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for svc, result in zip(services, results):
        sid = str(svc["id"])
        if isinstance(result, BaseException):
            errors.append({"service_id": sid, "error": str(result)})
        else:
            synced.append(result)
            await _notify_low_balance_from_sync(result)
    return {"synced": synced, "errors": errors, "count": len(synced)}


# --- Wallet ---


@router.get("/services/{service_id}/transactions")
async def list_transactions(
    service_id: str,
    limit: int = Query(50, ge=1, le=500),
    type: str | None = Query(None, alias="type"),
) -> list[dict[str, Any]]:
    _require_service(service_id)
    try:
        rows = db.get_transactions(service_id, limit, tx_type=type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return rows


@router.post("/services/{service_id}/topup", status_code=201)
async def topup_service(service_id: str, body: TopupBody) -> dict[str, Any]:
    service = _require_service(service_id)
    tx = db.add_transaction(
        service_id=service_id,
        type="topup",
        amount_eur=body.amount_eur,
        description=body.description or "Recharge manuelle",
    )
    balance_row = db.get_balance(service_id)
    balance = float(balance_row.get("balance_eur") or 0) if balance_row else 0.0
    alerts = [
        _normalize_service(a)
        for a in evaluate_threshold_alerts(
            service_id,
            balance,
            service_name=str(service.get("name") or service_id),
        )
    ]
    return {
        "transaction": tx,
        "balance": balance_row,
        "alerts_created": alerts,
    }


# --- Seuils & alertes ---


@router.get("/services/{service_id}/thresholds")
async def get_service_thresholds(service_id: str) -> dict[str, Any]:
    _require_service(service_id)
    return db.get_thresholds(service_id)


@router.put("/services/{service_id}/thresholds")
async def update_service_thresholds(
    service_id: str,
    body: ThresholdsBody,
) -> dict[str, Any]:
    _require_service(service_id)
    return db.set_thresholds(
        service_id,
        warning_eur=body.warning_eur,
        critical_eur=body.critical_eur,
        urgent_eur=body.urgent_eur,
    )


@router.get("/alerts")
async def list_unread_alerts(
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return [_normalize_service(a) for a in db.get_unread_alerts(limit)]


@router.post("/alerts/read")
async def mark_alerts_read(body: MarkAlertsReadBody | None = None) -> dict[str, Any]:
    ids = body.alert_ids if body and body.alert_ids else None
    count = db.mark_alerts_read(ids)
    return {"marked_read": count}


# --- Dashboard ---


@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    services = db.get_all_services()
    loop = asyncio.get_running_loop()
    pings = await asyncio.gather(
        *[
            loop.run_in_executor(_sync_pool, _ping_service, svc)
            for svc in services
        ]
    )
    enriched = [
        _service_payload(svc, ping=ping_ok)
        for svc, ping_ok in zip(services, pings)
    ]
    expenses = db.get_expense_aggregates()
    alerts = [_normalize_service(a) for a in db.get_unread_alerts(100)]

    return {
        "services": enriched,
        "balances": db.get_all_balances(),
        "unread_alerts": alerts,
        "unread_alerts_count": len(alerts),
        "expenses": expenses,
        "spent_today_eur": expenses["today_eur"],
        "spent_week_eur": expenses["week_eur"],
        "spent_month_eur": expenses["month_eur"],
        "month_total_eur": expenses["month_total_eur"],
    }
