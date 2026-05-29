"""
Suivi des coûts API par projet (mémoire processus).

Appeler track_cost(project_id, service, details) après chaque appel API externe.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

# project_id -> état agrégé
costs_by_project: dict[str, dict[str, Any]] = {}

_lock = threading.Lock()

EUR_PER_USD = 0.92

# Tarifs LLM (USD / million de tokens)
_CLAUDE_SONNET_INPUT_USD_PER_M = 3.0
_CLAUDE_SONNET_OUTPUT_USD_PER_M = 15.0
_DEEPSEEK_V3_INPUT_USD_PER_M = 0.27
_DEEPSEEK_V3_OUTPUT_USD_PER_M = 1.10

# Tarifs fixes (EUR)
_V0_EUR_PER_REQUEST = 0.01
_REPLICATE_EUR_PER_IMAGE = 0.002
_TAVILY_EUR_PER_REQUEST = 0.001

_FREE_SERVICES = frozenset({
    "unsplash",
    "brevo",
    "github",
    "vercel",
    "railway",
})

_SERVICE_ALIASES: dict[str, str] = {
    "claude": "claude_sonnet",
    "claude_sonnet": "claude_sonnet",
    "anthropic": "claude_sonnet",
    "claude-sonnet-4-20250514": "claude_sonnet",
    "deepseek": "deepseek_v3",
    "deepseek_v3": "deepseek_v3",
    "deepseek-chat": "deepseek_v3",
    "deepseek_chat": "deepseek_v3",
    "v0": "v0",
    "vercel_v0": "v0",
    "replicate": "replicate",
    "tavily": "tavily",
    "unsplash": "unsplash",
    "brevo": "brevo",
    "github": "github",
    "vercel": "vercel",
    "railway": "railway",
}


def _normalize_service(service: str) -> str:
    key = service.strip().lower().replace(" ", "_").replace("-", "_")
    return _SERVICE_ALIASES.get(key, key)


def _token_counts(details: dict[str, Any]) -> tuple[int, int]:
    input_tokens = int(
        details.get("input_tokens")
        or details.get("prompt_tokens")
        or 0
    )
    output_tokens = int(
        details.get("output_tokens")
        or details.get("completion_tokens")
        or 0
    )
    return max(0, input_tokens), max(0, output_tokens)


def _usd_to_eur(usd: float) -> float:
    return usd * EUR_PER_USD


def _llm_cost_eur(input_usd_per_m: float, output_usd_per_m: float, details: dict[str, Any]) -> float:
    inp, out = _token_counts(details)
    usd = (inp * input_usd_per_m + out * output_usd_per_m) / 1_000_000
    return _usd_to_eur(usd)


def _unit_count(details: dict[str, Any], *keys: str, default: int = 1) -> int:
    for key in keys:
        if key in details and details[key] is not None:
            return max(0, int(details[key]))
    return max(0, default)


def _compute_cost_eur(service: str, details: dict[str, Any]) -> float:
    svc = _normalize_service(service)

    if svc == "claude_sonnet":
        return _llm_cost_eur(
            _CLAUDE_SONNET_INPUT_USD_PER_M,
            _CLAUDE_SONNET_OUTPUT_USD_PER_M,
            details,
        )
    if svc == "deepseek_v3":
        return _llm_cost_eur(
            _DEEPSEEK_V3_INPUT_USD_PER_M,
            _DEEPSEEK_V3_OUTPUT_USD_PER_M,
            details,
        )
    if svc == "v0":
        return _V0_EUR_PER_REQUEST * _unit_count(details, "requests", "count")
    if svc == "replicate":
        return _REPLICATE_EUR_PER_IMAGE * _unit_count(details, "images", "count")
    if svc == "tavily":
        return _TAVILY_EUR_PER_REQUEST * _unit_count(details, "requests", "count")
    if svc in _FREE_SERVICES:
        return 0.0

    return 0.0


_ARCHITECT_PLAN_API_FIELDS = (
    "complexity_score",
    "complexity_label",
    "market_price_min",
    "market_price_max",
    "suggested_price_min",
    "suggested_price_max",
)


def _empty_project_state() -> dict[str, Any]:
    return {
        "total_eur": 0.0,
        "by_service": {},
        "updated_at": None,
        "architect_plan": None,
    }


def _ensure_project(project_id: str) -> dict[str, Any]:
    if project_id not in costs_by_project:
        costs_by_project[project_id] = _empty_project_state()
    return costs_by_project[project_id]


def track_cost(project_id: str, service: str, details: dict[str, Any] | None = None) -> float:
    """
    Enregistre le coût d'un appel API pour un projet.

    ``details`` selon le service :
    - claude_sonnet / deepseek_v3 : input_tokens, output_tokens (ou prompt_tokens / completion_tokens)
    - v0 / tavily : requests (défaut 1)
    - replicate : images (défaut 1)

    Retourne le coût en EUR de cet appel.
    """
    payload = details or {}
    cost = round(_compute_cost_eur(service, payload), 8)
    svc_key = _normalize_service(service)
    now = datetime.now(timezone.utc).isoformat()

    with _lock:
        entry = _ensure_project(project_id)
        entry["total_eur"] = round(entry["total_eur"] + cost, 8)
        by_svc: dict[str, dict[str, Any]] = entry["by_service"]
        if svc_key not in by_svc:
            by_svc[svc_key] = {"cost_eur": 0.0, "calls": 0}
        by_svc[svc_key]["cost_eur"] = round(by_svc[svc_key]["cost_eur"] + cost, 8)
        by_svc[svc_key]["calls"] += 1
        entry["updated_at"] = now

    return cost


def get_cost_summary(project_id: str) -> dict[str, Any]:
    """Résumé : coût total EUR, détail par service, timestamp de dernière mise à jour."""
    with _lock:
        entry = costs_by_project.get(project_id)
        if entry is None:
            return {
                "total_eur": 0.0,
                "by_service": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "total_eur": entry["total_eur"],
            "by_service": {
                name: dict(stats) for name, stats in entry["by_service"].items()
            },
            "timestamp": entry["updated_at"]
            or datetime.now(timezone.utc).isoformat(),
        }


def reset_cost(project_id: str) -> None:
    """Remet à zéro le suivi des coûts pour un projet."""
    with _lock:
        costs_by_project.pop(project_id, None)


def set_architect_plan(project_id: str, plan: dict[str, Any] | Any) -> None:
    """Enregistre le sous-ensemble tarifaire du plan ArchitectAI pour un projet."""
    if hasattr(plan, "model_dump"):
        raw = plan.model_dump(mode="json")
    elif isinstance(plan, dict):
        raw = plan
    else:
        return

    subset = {
        key: raw[key]
        for key in _ARCHITECT_PLAN_API_FIELDS
        if key in raw
    }
    if not subset:
        return

    with _lock:
        entry = _ensure_project(project_id)
        entry["architect_plan"] = subset


def build_costs_api_response(project_id: str) -> dict[str, Any]:
    """Payload GET /projects/{project_id}/costs."""
    summary = get_cost_summary(project_id)
    with _lock:
        entry = costs_by_project.get(project_id)
        architect_plan = (
            dict(entry["architect_plan"])
            if entry and entry.get("architect_plan")
            else None
        )

    total_eur = float(summary["total_eur"])
    by_service = {
        name: float(stats["cost_eur"])
        for name, stats in summary["by_service"].items()
    }

    margin_multiplier: int | None = None
    if total_eur > 0 and architect_plan is not None:
        suggested_min = architect_plan.get("suggested_price_min")
        if suggested_min is not None:
            margin_multiplier = round(int(suggested_min) / total_eur)

    return {
        "project_id": project_id,
        "total_eur": total_eur,
        "by_service": by_service,
        "architect_plan": architect_plan,
        "margin_multiplier": margin_multiplier,
        "updated_at": summary["timestamp"],
    }


def maybe_track_cost(
    project_id: str | None,
    service: str,
    details: dict[str, Any] | None = None,
) -> float:
    """Enregistre un coût uniquement si ``project_id`` est renseigné."""
    if not project_id:
        return 0.0
    return track_cost(project_id, service, details)


def usage_from_openai_payload(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") or {}
    return {
        "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        "output_tokens": int(
            usage.get("completion_tokens") or usage.get("output_tokens") or 0
        ),
    }


def usage_from_anthropic_payload(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }
