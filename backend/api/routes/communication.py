"""
Routes API — Agent Communication Protocol (canaux, messages, acks, analytics).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.orchestration_store import get_orchestration_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["communication"])


class AckRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    status: str = Field(default="received")


@router.get("/communication/channels")
async def list_communication_channels() -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.list_channels()
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("list_communication_channels: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/communication/sessions/{generation_id}/messages")
async def list_session_messages(
    generation_id: str,
    receiver_agent: str | None = Query(default=None),
    channel_name: str | None = Query(default=None),
) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        session = await store.get_session(generation_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session pour '{generation_id}' introuvable.",
            )
        messages = await store.get_messages(
            str(session["id"]),
            receiver_agent=receiver_agent,
            channel_name=channel_name,
        )
        return {"items": messages, "count": len(messages)}
    except SupabaseStoreError as exc:
        logger.warning("list_session_messages: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/communication/messages/{message_id}/ack")
async def ack_message(message_id: str, body: AckRequest) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.ack_message(
            message_id,
            body.agent_id,
            status=body.status,
        )
    except SupabaseStoreError as exc:
        logger.warning("ack_message: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail=f"Message '{message_id}' introuvable.")
    return row


@router.get("/communication/analytics")
async def get_communication_analytics(days: int = Query(default=30, ge=1, le=365)) -> dict:
    store = get_orchestration_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        items = await store.get_communication_analytics(days=days)
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        logger.warning("get_communication_analytics: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
