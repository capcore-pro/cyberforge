"""
Routes API — Mode Client (validation démo par le client).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agents.email_ai import notify_client_review_response
from db.audit_store import get_audit_store
from db.client_review_store import (
    ClientReviewStore,
    get_client_review_store,
)
from db.demo_tracking_store import get_demo_tracking_store
from db.supabase_store import SupabaseStoreError, get_supabase_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["client-review"])


class CreateClientReviewBody(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=128)
    client_name: str | None = Field(default=None, max_length=255)
    client_email: str | None = Field(default=None, max_length=255)
    expires_days: int = Field(default=30, ge=1, le=365)


class RespondClientReviewBody(BaseModel):
    status: Literal["approved", "revision_requested"]
    feedback: str | None = Field(default=None, max_length=8000)
    rating: int | None = Field(default=None, ge=1, le=5)


def _store_error(exc: SupabaseStoreError) -> HTTPException:
    msg = str(exc)
    if "introuvable" in msg.lower():
        return HTTPException(status_code=404, detail=msg)
    if "expiré" in msg.lower() or "déjà" in msg.lower():
        return HTTPException(status_code=409, detail=msg)
    return HTTPException(status_code=400, detail=msg)


async def _project_context(project_id: str) -> tuple[str, str | None]:
    store = get_supabase_store()
    if not store.is_configured():
        return "Projet CyberForge", None
    detail = await store.get_project(project_id)
    if detail is None:
        return "Projet CyberForge", None
    title = (detail.project.title or "").strip() or "Projet CyberForge"
    demo_url = (detail.project.demo_url or "").strip() or None
    return title, demo_url


def _public_review_payload(
    review: dict[str, Any],
    *,
    project_title: str,
    demo_url: str | None,
) -> dict[str, Any]:
    store = get_client_review_store()
    expired = ClientReviewStore._is_expired(review)
    status = str(review.get("status") or "pending")
    responded = bool(review.get("responded_at")) or status != "pending"
    return {
        "project_id": str(review.get("project_id") or ""),
        "client_name": review.get("client_name"),
        "demo_url": demo_url,
        "project_title": project_title,
        "status": status,
        "viewed_at": review.get("viewed_at"),
        "expires_at": review.get("expires_at"),
        "expired": expired,
        "responded": responded,
        "rating": review.get("rating"),
        "feedback": review.get("feedback"),
    }


@router.post("/client-review/create")
async def create_client_review(body: CreateClientReviewBody) -> dict[str, Any]:
    store = get_client_review_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        created = await store.create_review(
            body.project_id,
            body.client_name,
            body.client_email,
            expires_days=body.expires_days,
        )
    except SupabaseStoreError as exc:
        raise _store_error(exc) from exc

    return {
        "token": created["token"],
        "review_url": created["url"],
        "expires_at": created["expires_at"],
        "id": created["id"],
    }


@router.get("/client-review/{token}")
async def get_client_review(token: str, request: Request) -> dict[str, Any]:
    store = get_client_review_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    review = await store.get_review_by_token(token)
    if not review:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré.")

    if ClientReviewStore._is_expired(review):
        raise HTTPException(status_code=410, detail="Ce lien a expiré.")

    try:
        await store.mark_viewed(token)
    except SupabaseStoreError as exc:
        logger.warning("mark_viewed ignoré: %s", exc)

    project_title, demo_url = await _project_context(str(review.get("project_id") or ""))

    if demo_url:
        tracking = get_demo_tracking_store()
        forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
        visitor_ip = forwarded.split(",")[0].strip() if forwarded else None
        if not visitor_ip and request.client:
            visitor_ip = request.client.host

        async def _record_demo_view() -> None:
            try:
                await tracking.record_view(
                    project_id=str(review.get("project_id") or ""),
                    demo_url=demo_url,
                    visitor_ip=visitor_ip,
                    user_agent=request.headers.get("User-Agent"),
                    referer=request.headers.get("Referer"),
                )
            except Exception as exc:
                logger.warning("[client-review] demo view tracking ignoré: %s", exc)

        asyncio.create_task(_record_demo_view())

    return _public_review_payload(
        review,
        project_title=project_title,
        demo_url=demo_url,
    )


@router.post("/client-review/{token}/respond")
async def respond_client_review(token: str, body: RespondClientReviewBody) -> dict[str, Any]:
    store = get_client_review_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    try:
        updated = await store.submit_feedback(
            token,
            body.status,
            feedback=body.feedback,
            rating=body.rating,
        )
    except SupabaseStoreError as exc:
        raise _store_error(exc) from exc

    project_id = str(updated.get("project_id") or "")
    project_title, demo_url = await _project_context(project_id)
    event_type = (
        "client_approved"
        if body.status == "approved"
        else "client_revision_requested"
    )
    await get_audit_store().log(
        event_type,
        actor_type="client",
        actor_id=str(updated.get("client_email") or updated.get("client_name") or "client"),
        project_id=project_id,
        event_data={
            "token": token,
            "status": body.status,
            "rating": body.rating,
            "feedback": body.feedback,
            "client_name": updated.get("client_name"),
        },
    )

    try:
        await notify_client_review_response(
            project_title=project_title,
            client_name=str(updated.get("client_name") or "Client"),
            status=body.status,
            feedback=body.feedback,
            rating=body.rating,
            demo_url=demo_url or "",
        )
    except Exception as exc:
        logger.warning("[client-review] notification EmailAI ignorée: %s", exc)

    message = (
        "Parfait ! Mat Gibiard a été notifié de votre approbation."
        if body.status == "approved"
        else "Vos commentaires ont été envoyés à Mat Gibiard."
    )
    return {"ok": True, "status": body.status, "message": message}


@router.get("/client-review/project/{project_id}")
async def list_project_client_reviews(project_id: str) -> dict[str, Any]:
    store = get_client_review_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    items = await store.list_reviews(project_id)
    return {"items": items, "count": len(items)}
