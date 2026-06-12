"""
Routes API — Agent Registry (registre officiel des agents IA).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.agent_registry_store import get_agent_registry_store
from db.audit_store import get_audit_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent_registry"])


class UpdateModelRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)


class SetEnabledRequest(BaseModel):
    enabled: bool


@router.get("/agents/registry")
async def list_agent_registry() -> dict:
    store = get_agent_registry_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_all()
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_agent_registry: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/agents/registry/pipeline")
async def list_pipeline_agents() -> dict:
    store = get_agent_registry_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.get_pipeline_agents()
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_pipeline_agents: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/agents/registry/{agent_id}")
async def get_agent_registry_entry(agent_id: str) -> dict:
    store = get_agent_registry_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_by_agent_id(agent_id)
    except SupabaseStoreError as exc:
        logger.warning("get_agent_registry_entry: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' introuvable.")
    return row


@router.patch("/agents/registry/{agent_id}/model")
async def update_agent_model(agent_id: str, body: UpdateModelRequest) -> dict:
    store = get_agent_registry_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        existing = await store.get_by_agent_id(agent_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' introuvable.")
        updated = await store.update_model(agent_id, body.model, body.provider)
    except SupabaseStoreError as exc:
        logger.warning("update_agent_model: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    audit = get_audit_store()
    await audit.log(
        "agent_model_updated",
        event_data={
            "agent_id": agent_id,
            "previous_model": existing.get("model"),
            "previous_provider": existing.get("provider"),
            "model": body.model,
            "provider": body.provider,
        },
    )
    return updated


@router.patch("/agents/registry/{agent_id}/enable")
async def set_agent_enabled(agent_id: str, body: SetEnabledRequest) -> dict:
    store = get_agent_registry_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        existing = await store.get_by_agent_id(agent_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' introuvable.")
        updated = await store.set_enabled(agent_id, body.enabled)
    except SupabaseStoreError as exc:
        logger.warning("set_agent_enabled: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    audit = get_audit_store()
    await audit.log(
        "agent_enabled" if body.enabled else "agent_disabled",
        event_data={
            "agent_id": agent_id,
            "enabled": body.enabled,
            "previous_enabled": existing.get("enabled"),
        },
    )
    return updated
