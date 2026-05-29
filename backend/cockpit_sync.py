"""
Pont cost_tracker (mémoire) → cockpit_db (SQLite persistant).
"""

from __future__ import annotations

import logging
from typing import Any

import cockpit_db as db
from cost_tracker import get_cost_summary, reset_cost

logger = logging.getLogger(__name__)

# Clés cost_tracker.by_service → id service cockpit
_COST_KEY_TO_COCKPIT_ID: dict[str, str] = {
    "claude_sonnet": "anthropic",
    "anthropic": "anthropic",
    "deepseek_v3": "deepseek",
    "deepseek": "deepseek",
    "v0": "v0",
    "replicate": "replicate",
    "tavily": "tavily",
    "unsplash": "unsplash",
    "brevo": "brevo",
    "github": "github",
    "vercel": "vercel",
    "railway": "railway",
    "cloudflare": "cloudflare",
}


def evaluate_threshold_alerts(
    service_id: str,
    balance_eur: float,
    *,
    service_name: str | None = None,
) -> list[dict[str, Any]]:
    """Crée une alerte si le solde est sous un seuil (sans doublon non lu par niveau)."""
    thresholds = db.get_thresholds(service_id)
    name = service_name or service_id
    balance = float(balance_eur)

    balance_row = db.get_balance(service_id)
    last_synced = (balance_row or {}).get("last_synced_at")
    if balance <= 0 and not last_synced:
        return []

    level: str | None = None
    if balance <= float(thresholds["urgent_eur"]):
        level = "urgent"
    elif balance <= float(thresholds["critical_eur"]):
        level = "critical"
    elif balance <= float(thresholds["warning_eur"]):
        level = "warning"

    if level is None:
        return []

    if db.has_unread_alert(service_id, level):
        return []

    labels = {
        "warning": "avertissement",
        "critical": "critique",
        "urgent": "urgent",
    }
    message = (
        f"Solde {name} : {balance:.2f} € — seuil {labels[level]} "
        f"({thresholds[f'{level}_eur']} €)."
    )
    alert = db.add_alert(service_id=service_id, level=level, message=message)
    return [alert]


def _aggregate_costs_by_cockpit(by_service: dict[str, Any]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for key, stats in (by_service or {}).items():
        if not isinstance(stats, dict):
            continue
        cost = float(stats.get("cost_eur") or 0)
        if cost <= 0:
            continue
        cockpit_id = _COST_KEY_TO_COCKPIT_ID.get(key, key)
        totals[cockpit_id] = round(totals.get(cockpit_id, 0.0) + cost, 8)
    return totals


def flush_project_costs(project_id: str) -> dict[str, Any]:
    """
    Persiste les coûts d'un projet en transactions cockpit, met à jour les soldes,
    évalue les seuils, puis remet à zéro le cost_tracker pour ce projet.
    """
    pid = (project_id or "").strip()
    if not pid:
        return {"project_id": "", "flushed": [], "skipped": [], "alerts": []}

    summary = get_cost_summary(pid)
    by_cockpit = _aggregate_costs_by_cockpit(summary.get("by_service") or {})

    flushed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    alerts_created: list[dict[str, Any]] = []

    for service_id, cost in by_cockpit.items():
        if cost <= 0:
            continue

        svc = db.get_service(service_id)
        if svc is None:
            skipped.append(
                {"service_id": service_id, "cost_eur": cost, "reason": "unknown_service"}
            )
            continue
        assert svc is not None
        svc_name = str(svc.get("name") or service_id)

        balance_row = db.get_balance(service_id)
        balance_before = float(balance_row.get("balance_eur") or 0) if balance_row else 0.0
        balance_after = round(balance_before - cost, 8)

        try:
            tx = db.add_transaction(
                service_id=service_id,
                type="expense",
                amount_eur=cost,
                description=f"Projet {pid}",
                project_id=pid,
            )
            db.set_balance(service_id, balance_after)
            new_alerts = evaluate_threshold_alerts(
                service_id,
                balance_after,
                service_name=svc_name,
            )
            alerts_created.extend(new_alerts)
            flushed.append(
                {
                    "service_id": service_id,
                    "cost_eur": cost,
                    "balance_before_eur": balance_before,
                    "balance_after_eur": balance_after,
                    "transaction_id": tx.get("id"),
                }
            )
        except Exception as exc:
            logger.warning(
                "flush_project_costs %s / %s : %s",
                pid,
                service_id,
                exc,
                exc_info=True,
            )
            skipped.append(
                {
                    "service_id": service_id,
                    "cost_eur": cost,
                    "reason": str(exc),
                }
            )

    reset_cost(pid)

    return {
        "project_id": pid,
        "total_eur": float(summary.get("total_eur") or 0),
        "flushed": flushed,
        "skipped": skipped,
        "alerts": alerts_created,
    }
