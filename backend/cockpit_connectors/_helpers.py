"""Utilitaires partagés — repli SQLite et agrégation cost_tracker."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cost_tracker import EUR_PER_USD, costs_by_project

logger = logging.getLogger(__name__)

# service_id cockpit → clés cost_tracker.by_service
_COST_TRACKER_KEYS: dict[str, tuple[str, ...]] = {
    "anthropic": ("claude_sonnet", "anthropic"),
    "deepseek": ("deepseek_v3", "deepseek"),
    "v0": ("v0",),
    "replicate": ("replicate",),
    "tavily": ("tavily",),
    "railway": ("railway",),
    "vercel": ("vercel",),
    "cloudflare": ("cloudflare",),
    "brevo": ("brevo",),
    "github": ("github",),
    "unsplash": ("unsplash",),
}


def cached_balance_eur(service_id: str) -> float:
    from cockpit_db import get_balance

    row = get_balance(service_id)
    if not row:
        return 0.0
    return float(row.get("balance_eur") or 0.0)


def cost_tracker_spent_eur(service_id: str) -> float:
    """Somme des coûts API enregistrés (tous projets) pour ce service."""
    keys = _COST_TRACKER_KEYS.get(service_id, (service_id,))
    total = 0.0
    for entry in costs_by_project.values():
        by_svc = entry.get("by_service") or {}
        for key in keys:
            stats = by_svc.get(key)
            if isinstance(stats, dict):
                total += float(stats.get("cost_eur") or 0)
    return round(total, 8)


def transactions_usage(service_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    from cockpit_db import get_transactions

    rows = get_transactions(service_id, limit)
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": row.get("id"),
                "type": row.get("type"),
                "amount_eur": float(row.get("amount_eur") or 0),
                "description": row.get("description"),
                "project_id": row.get("project_id"),
                "created_at": row.get("created_at"),
            }
        )
    return items


def build_usage_payload(
    *,
    source: str,
    service_id: str,
    total_eur: float = 0.0,
    items: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": source,
        "service_id": service_id,
        "total_eur": round(float(total_eur), 8),
        "cost_tracker_eur": cost_tracker_spent_eur(service_id),
        "items": items or [],
    }
    if extra:
        payload.update(extra)
    if error:
        payload["error"] = error
    return payload


def usd_to_eur(amount_usd: float) -> float:
    return round(float(amount_usd) * EUR_PER_USD, 8)


def http_get_json(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float = 15.0,
    params: dict[str, str] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, params=params)
        if response.status_code >= 400:
            return None, f"HTTP {response.status_code}"
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}, None
    except httpx.HTTPError as exc:
        return None, str(exc)
    except ValueError as exc:
        return None, f"JSON invalide: {exc}"


def http_post_json(
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: float = 20.0,
) -> tuple[dict[str, Any] | None, int, str | None]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=body)
        status = response.status_code
        if status >= 400:
            return None, status, f"HTTP {status}"
        try:
            data = response.json()
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {"data": data}, status, None
    except httpx.HTTPError as exc:
        return None, 0, str(exc)
