"""
API newsletter CapCore — contacts, séquences bienvenue, envoi Brevo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import newsletter_agent as agent
import newsletter_db as db
from config import get_settings
from newsletter_agent import NewsletterAgentError
from tools.capcore_notify import send_html_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["newsletter"])

SequenceStatus = Literal["pending", "in_progress", "completed", "cancelled"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


# --- Schémas ---


class ContactBody(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    company: str | None = None
    sector: str | None = None
    project_id: str | None = None
    project_type: str | None = None
    personality_notes: str | None = None
    subscribed: bool = True


class ContactUpdateBody(BaseModel):
    email: str | None = Field(default=None, min_length=3)
    name: str | None = Field(default=None, min_length=1)
    company: str | None = None
    sector: str | None = None
    project_id: str | None = None
    project_type: str | None = None
    personality_notes: str | None = None
    subscribed: bool | None = None


class TriggerSequenceBody(BaseModel):
    email: str | None = Field(
        default=None,
        description="Email client (sinon auth projet / contexte livraison)",
    )
    name: str | None = None


class NewsletterGenerateBody(BaseModel):
    theme: str = Field(min_length=1)
    context: str = ""


class NewProspectBody(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    company: str | None = None
    sector: str | None = None
    message: str | None = None


# --- Helpers ---


async def _send_newsletter_email_row(
    email_row: dict[str, Any],
    *,
    contact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cid = email_row.get("contact_id")
    if not contact and cid:
        contact = db.get_contact(str(cid))
    if contact is None:
        raise HTTPException(status_code=400, detail="Contact introuvable pour cet email.")
    if not contact.get("subscribed", True):
        return {"email_id": email_row["id"], "skipped": True, "reason": "unsubscribed"}

    to_email = str(contact.get("email") or "").strip()
    if not to_email or to_email.endswith("@placeholder.capcore.local"):
        raise HTTPException(
            status_code=400,
            detail="Email contact invalide ou placeholder — renseignez un email réel.",
        )

    try:
        message_id = await send_html_email(
            to_email=to_email,
            to_name=str(contact.get("name") or ""),
            subject=str(email_row["subject"]),
            html_content=str(email_row["html_content"]),
            project_id=str(contact.get("project_id")) if contact.get("project_id") else None,
        )
    except RuntimeError as exc:
        db.update_email(str(email_row["id"]), status="failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    now = _utc_now()
    db.update_email(
        str(email_row["id"]),
        status="sent",
        sent_at=now,
        brevo_message_id=message_id,
    )
    return {
        "email_id": email_row["id"],
        "sent": True,
        "to": to_email,
        "brevo_message_id": message_id,
        "sent_at": now,
    }


async def _resolve_contact_for_project(
    project_id: str,
    *,
    email: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    ctx = await agent._fetch_project_context(project_id)
    resolved_email = (email or ctx.get("client_email") or "").strip().lower()
    if not resolved_email:
        raise HTTPException(
            status_code=400,
            detail="Email client requis (body.email ou auth projet / contexte).",
        )
    resolved_name = (name or ctx.get("client_name") or ctx.get("company") or "Client").strip()

    existing = db.get_contact_by_email(resolved_email)
    if existing:
        updated = db.update_contact(
            str(existing["id"]),
            name=resolved_name,
            company=ctx.get("company"),
            sector=ctx.get("sector"),
            project_id=project_id,
            project_type=str(ctx.get("project_type") or ""),
        )
        return updated or existing

    try:
        return db.add_contact(
            email=resolved_email,
            name=resolved_name,
            company=ctx.get("company"),
            sector=ctx.get("sector"),
            project_id=project_id,
            project_type=str(ctx.get("project_type") or ""),
        )
    except ValueError as exc:
        raise _value_error(exc) from exc


# --- Contacts ---


@router.get("/contacts")
def list_contacts() -> list[dict[str, Any]]:
    return db.list_contacts()


@router.post("/contacts", status_code=201)
def create_contact(body: ContactBody) -> dict[str, Any]:
    try:
        return db.add_contact(
            email=body.email,
            name=body.name,
            company=body.company,
            sector=body.sector,
            project_id=body.project_id,
            project_type=body.project_type,
            personality_notes=body.personality_notes,
            subscribed=body.subscribed,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.put("/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactUpdateBody) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = db.get_contact(contact_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Contact introuvable.")
        return row
    try:
        updated = db.update_contact(contact_id, **fields)
    except ValueError as exc:
        raise _value_error(exc) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Contact introuvable.")
    return updated


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str) -> None:
    if not db.delete_contact(contact_id):
        raise HTTPException(status_code=404, detail="Contact introuvable.")


# --- Séquences bienvenue ---


async def trigger_welcome_sequence(
    project_id: str,
    *,
    email: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """
    Déclenche la séquence bienvenue pour un projet livré (appel pipeline ou API).
    Analyse personnalité, génère 3 emails (J0 / +24h / +72h), envoie J0 via Brevo.
    """
    contact = await _resolve_contact_for_project(
        project_id,
        email=email,
        name=name,
    )
    await agent.analyze_contact(project_id)
    contact = db.get_contact(str(contact["id"])) or contact

    emails = await agent.generate_welcome_sequence(
        str(contact["id"]),
        trigger="project_delivered",
        schedule_offsets_hours=agent._DEFAULT_SCHEDULE_HOURS,
    )

    j0 = next((e for e in emails if e.get("type") == "welcome_j0"), None)
    j0_sent: dict[str, Any] | None = None
    if j0:
        j0_sent = await _send_newsletter_email_row(j0, contact=contact)

    sequence_id = str(emails[0].get("sequence_id") or "") if emails else ""
    return {
        "contact": contact,
        "sequence_id": sequence_id,
        "emails_scheduled": len(emails),
        "j0_sent": j0_sent is not None and j0_sent.get("sent"),
        "emails": emails,
    }


@router.post("/sequences/trigger/{project_id}")
async def trigger_welcome_sequence_route(
    project_id: str,
    body: TriggerSequenceBody | None = None,
) -> dict[str, Any]:
    """Route HTTP — enveloppe trigger_welcome_sequence avec erreurs FastAPI."""
    payload = body or TriggerSequenceBody()
    try:
        return await trigger_welcome_sequence(
            project_id,
            email=payload.email,
            name=payload.name,
        )
    except NewsletterAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise _value_error(exc) from exc
    except HTTPException:
        raise


@router.get("/sequences")
def list_sequences(
    status: SequenceStatus | None = Query(default=None),
) -> list[dict[str, Any]]:
    try:
        return db.list_sequences(status=status)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/sequences/{sequence_id}/emails")
def list_sequence_emails(sequence_id: str) -> list[dict[str, Any]]:
    seq = db.get_sequence(sequence_id)
    if seq is None:
        raise HTTPException(status_code=404, detail="Séquence introuvable.")
    return db.list_emails(sequence_id=sequence_id)


# --- Envoi schedulé ---


@router.post("/send-pending")
async def send_pending_emails() -> dict[str, Any]:
    """Envoie tous les emails scheduled dont scheduled_at <= maintenant."""
    pending = db.list_pending_emails(limit=500)
    results: list[dict[str, Any]] = []
    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for row in pending:
        try:
            outcome = await _send_newsletter_email_row(row)
            results.append(outcome)
            if outcome.get("skipped"):
                skipped_count += 1
            elif outcome.get("sent"):
                sent_count += 1
        except HTTPException as exc:
            failed_count += 1
            results.append(
                {"email_id": row.get("id"), "sent": False, "error": exc.detail}
            )
        except Exception as exc:
            failed_count += 1
            db.update_email(str(row["id"]), status="failed")
            results.append(
                {"email_id": row.get("id"), "sent": False, "error": str(exc)}
            )

    return {
        "processed": len(pending),
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "results": results,
    }


# --- Newsletter ponctuelle ---


@router.post("/newsletter/generate")
async def generate_newsletter(body: NewsletterGenerateBody) -> dict[str, Any]:
    try:
        return await agent.generate_newsletter(body.theme, body.context)
    except NewsletterAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/newsletter/{email_id}/send-all")
async def send_newsletter_to_all(email_id: str) -> dict[str, Any]:
    email_row = db.get_email(email_id)
    if email_row is None:
        raise HTTPException(status_code=404, detail="Email introuvable.")
    if email_row.get("type") != "newsletter":
        raise HTTPException(status_code=400, detail="Cet email n'est pas une newsletter.")

    contacts = db.list_contacts(limit=2000, subscribed_only=True)
    results: list[dict[str, Any]] = []
    sent = 0
    failed = 0

    for contact in contacts:
        to_email = str(contact.get("email") or "").strip()
        if not to_email or to_email.endswith("@placeholder.capcore.local"):
            results.append({"contact_id": contact["id"], "skipped": True})
            continue
        try:
            message_id = await send_html_email(
                to_email=to_email,
                to_name=str(contact.get("name") or ""),
                subject=str(email_row["subject"]),
                html_content=str(email_row["html_content"]),
            )
            sent += 1
            results.append(
                {
                    "contact_id": contact["id"],
                    "to": to_email,
                    "sent": True,
                    "brevo_message_id": message_id,
                }
            )
        except Exception as exc:
            failed += 1
            results.append(
                {"contact_id": contact["id"], "to": to_email, "sent": False, "error": str(exc)}
            )

    now = _utc_now()
    db.update_email(email_id, status="sent", sent_at=now)

    return {
        "email_id": email_id,
        "recipients": len(contacts),
        "sent": sent,
        "failed": failed,
        "results": results,
    }


@router.post("/newsletter/{email_id}/preview")
async def preview_newsletter(email_id: str) -> dict[str, Any]:
    email_row = db.get_email(email_id)
    if email_row is None:
        raise HTTPException(status_code=404, detail="Email introuvable.")

    settings = get_settings()
    mat_email = (settings.capcore_notify_email or "capcore.pro@gmail.com").strip()

    try:
        message_id = await send_html_email(
            to_email=mat_email,
            to_name=settings.mat_legal_name,
            subject=f"[Preview] {email_row['subject']}",
            html_content=str(email_row["html_content"]),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "preview_sent": True,
        "to": mat_email,
        "brevo_message_id": message_id,
    }


# --- Webhook prospect ---


@router.post("/webhook/new-prospect", status_code=201)
async def webhook_new_prospect(body: NewProspectBody) -> dict[str, Any]:
    """Formulaire capcore.pro — contact + séquence web_form + envoi J0."""
    existing = db.get_contact_by_email(body.email)
    if existing:
        contact = db.update_contact(
            str(existing["id"]),
            name=body.name,
            company=body.company,
            sector=body.sector,
        ) or existing
    else:
        try:
            contact = db.add_contact(
                email=body.email,
                name=body.name,
                company=body.company,
                sector=body.sector,
            )
        except ValueError as exc:
            raise _value_error(exc) from exc

    if body.message:
        notes = f"Message formulaire : {body.message.strip()}"
        db.update_contact(str(contact["id"]), personality_notes=notes)

    seq = db.create_sequence(str(contact["id"]), "web_form", status="in_progress")

    try:
        emails = await agent.generate_welcome_sequence(
            str(contact["id"]),
            trigger="web_form",
            sequence_id=str(seq["id"]),
            schedule_offsets_hours=agent._DEFAULT_SCHEDULE_HOURS,
        )
    except NewsletterAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    j0 = next((e for e in emails if e.get("type") == "welcome_j0"), None)
    j0_sent = False
    if j0:
        try:
            result = await _send_newsletter_email_row(j0, contact=contact)
            j0_sent = bool(result.get("sent"))
        except HTTPException:
            logger.exception("Envoi J0 webhook prospect échoué")

    return {
        "contact": contact,
        "sequence_id": seq["id"],
        "emails_scheduled": len(emails),
        "j0_sent": j0_sent,
    }
