"""
Routes vitrines Next.js — contact public (proxy Vercel → Railway).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from tools.capcore_notify import send_capcore_contact_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vitrine"])


class VitrineContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=8000)
    site: str | None = Field(default=None, max_length=300)


class VitrineContactResponse(BaseModel):
    recorded: bool = True
    email_sent: bool = False


@router.post("/vitrine/contact", response_model=VitrineContactResponse)
async def vitrine_contact(body: VitrineContactRequest) -> VitrineContactResponse:
    """
    Endpoint public pour le formulaire Contact des vitrines.
    Envoie un email via Brevo (si configuré) vers CAPCORE_NOTIFY_EMAIL.
    """
    logger.info("vitrine contact | client=%s <%s>", body.name.strip(), body.email.strip())
    title = f"Vitrine — {body.site.strip()}" if body.site and body.site.strip() else "Vitrine"
    email_sent = await send_capcore_contact_email(
        project_title=title,
        client_name=body.name,
        client_email=body.email,
        message=body.message,
        demo_url=body.site or "",
        demo_password=None,
        unlock_url=None,
    )
    return VitrineContactResponse(recorded=True, email_sent=email_sent)

