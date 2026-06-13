"""
Routes API — App mobile CyberForge (push tokens, health).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile"])

push_tokens: list[str] = []


class RegisterPushTokenRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)
    platform: str = Field(default="android", max_length=32)


@router.post("/mobile/register-push-token")
async def register_push_token(body: RegisterPushTokenRequest) -> dict:
    token = body.token.strip()
    if token not in push_tokens:
        push_tokens.append(token)
        logger.info("Push token enregistré (%s) — total=%s", body.platform, len(push_tokens))
    return {"ok": True, "registered": len(push_tokens)}


@router.get("/mobile/health")
async def mobile_health() -> dict:
    return {"status": "ok", "tokens": len(push_tokens)}
