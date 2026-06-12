"""
Routes API — Workflow Engine (définitions, exécutions).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from db.supabase_store import SupabaseStoreError
from db.workflow_store import get_workflow_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workflows"])


@router.get("/workflows")
async def list_workflows() -> dict:
    store = get_workflow_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        workflows = await store.list_workflows(status="active")
        items: list[dict] = []
        for workflow in workflows:
            steps = await store.get_steps(str(workflow.get("id") or ""))
            items.append({**workflow, "steps": steps, "step_count": len(steps)})
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_workflows: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/workflows/execution/{generation_id}")
async def get_workflow_execution(generation_id: str) -> dict:
    store = get_workflow_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_execution(generation_id)
    except SupabaseStoreError as exc:
        logger.warning("get_workflow_execution: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Exécution workflow pour '{generation_id}' introuvable.",
        )
    return row


@router.get("/workflows/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    store = get_workflow_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        workflow = await store.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' introuvable.")
        items = await store.list_executions(workflow_id=workflow_id, limit=limit)
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_workflow_executions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/workflows/{workflow_id}")
async def get_workflow_detail(workflow_id: str) -> dict:
    store = get_workflow_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        workflow = await store.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' introuvable.")
        steps = await store.get_steps(str(workflow.get("id") or ""))
    except SupabaseStoreError as exc:
        logger.warning("get_workflow_detail: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {**workflow, "steps": steps, "step_count": len(steps)}
