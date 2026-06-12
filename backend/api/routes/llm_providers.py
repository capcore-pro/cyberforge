"""
Routes API — LLM providers et routing.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from db.llm_provider_store import get_llm_provider_store
from db.supabase_store import SupabaseStoreError
from llm.router import ROUTING_RULES, get_llm_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["llm_providers"])


@router.get("/llm/providers")
async def list_llm_providers() -> dict:
    store = get_llm_provider_store()
    router_inst = get_llm_router()
    available = set(router_inst.get_available_providers())

    if not store.is_configured():
        return {
            "items": [
                {
                    "slug": slug,
                    "name": slug.title(),
                    "available": slug in available,
                    "models_count": 0,
                }
                for slug in ("anthropic", "openai", "deepseek", "ollama")
            ],
            "count": 4,
        }

    try:
        providers = await store.list_providers()
        model_counts = await store.count_models_by_provider()
    except SupabaseStoreError as exc:
        logger.warning("list_llm_providers: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    items = []
    for row in providers:
        slug = str(row.get("slug") or "")
        pid = str(row.get("id") or "")
        items.append(
            {
                "slug": slug,
                "name": str(row.get("name") or slug),
                "available": slug in available,
                "models_count": model_counts.get(pid, 0),
                "enabled": bool(row.get("enabled", True)),
                "priority": int(row.get("priority") or 0),
            }
        )
    return {"items": items, "count": len(items)}


@router.get("/llm/routing")
async def get_llm_routing() -> dict:
    router_inst = get_llm_router()
    available = router_inst.get_available_providers()
    tasks: dict[str, dict] = {}
    for task_type, rule in ROUTING_RULES.items():
        primary = rule["primary"]
        fallback = rule["fallback"]
        tasks[task_type] = {
            "primary": primary,
            "primary_model": rule["primary_model"],
            "fallback": fallback,
            "fallback_model": rule["fallback_model"],
            "primary_available": primary in available,
            "fallback_available": fallback in available,
            "active_provider": primary if primary in available else fallback,
        }
    return {
        "rules": ROUTING_RULES,
        "tasks": tasks,
        "available_providers": available,
    }
