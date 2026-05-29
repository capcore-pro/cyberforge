"""
Notification email CapCore — formulaire « Contacter CapCore » sur une démo (API Brevo).
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from config import get_settings, plain_secret_str
from cost_tracker import maybe_track_cost

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "capcore.pro@gmail.com"
BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


def _brevo_configured() -> bool:
    return bool(plain_secret_str(get_settings().brevo_api_key))


def _resolve_sender() -> tuple[str, str]:
    settings = get_settings()
    to_default = (settings.capcore_notify_email or "").strip() or DEFAULT_NOTIFY_EMAIL
    email = (settings.brevo_sender_email or "").strip() or to_default
    name = (settings.brevo_sender_name or "CyberForge").strip() or "CyberForge"
    return name, email


def _build_contact_email(
    *,
    project_title: str,
    client_name: str,
    client_email: str,
    message: str,
    demo_url: str,
    demo_password: str | None,
    unlock_url: str | None,
) -> tuple[str, str]:
    title = (project_title or "Démo").strip() or "Démo"
    subject = f"🔔 Nouveau contact — {title}"
    pwd_line = demo_password.strip() if demo_password and demo_password.strip() else "(non archivé — voir CyberForge)"
    unlock_line = (unlock_url or "").strip() or demo_url
    body = (
        "Bonjour Mat,\n\n"
        "Un visiteur a soumis le formulaire « Contacter CapCore » sur une démo.\n\n"
        f"Projet : {title}\n"
        f"Nom : {client_name.strip()}\n"
        f"Email : {client_email.strip()}\n\n"
        "Message :\n"
        f"{message.strip()}\n\n"
        "---\n"
        "Accès à la démo\n"
        f"Lien : {demo_url.strip()}\n"
        f"Mot de passe : {pwd_line}\n"
        f"Lien CyberForge (déverrouillage) : {unlock_line}\n"
    )
    return subject, body


async def _send_brevo_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    project_id: str | None = None,
    attachment_path: str | Path | None = None,
    attachment_name: str | None = None,
) -> None:
    settings = get_settings()
    api_key = plain_secret_str(settings.brevo_api_key)
    if not api_key:
        raise RuntimeError("Brevo non configuré (BREVO_API_KEY).")

    sender_name, sender_email = _resolve_sender()
    payload: dict[str, object] = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    if attachment_path:
        path = Path(attachment_path)
        if not path.is_file():
            raise FileNotFoundError(f"Pièce jointe introuvable : {path}")
        payload["attachment"] = [
            {
                "name": attachment_name or path.name,
                "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        ]

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        resp = await client.post(
            BREVO_SEND_URL,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "accept": "application/json",
            },
            json=payload,
        )

    if resp.status_code >= 400:
        detail = resp.text.strip()[:500] or resp.reason_phrase
        raise RuntimeError(f"Brevo HTTP {resp.status_code}: {detail}")

    maybe_track_cost(project_id, "brevo", {"requests": 1})


async def send_document_email_to_client(
    *,
    to_email: str,
    subject: str,
    body: str,
    pdf_path: str | Path,
    attachment_name: str | None = None,
    project_id: str | None = None,
) -> bool:
    """Envoie un document juridique (PDF) au client via Brevo."""
    if not _brevo_configured():
        logger.warning("Brevo non configuré — email client non envoyé (%s)", to_email)
        return False
    try:
        await _send_brevo_email(
            to_email=to_email,
            subject=subject,
            body=body,
            project_id=project_id,
            attachment_path=pdf_path,
            attachment_name=attachment_name,
        )
        logger.info("Email document envoyé (Brevo) → %s (%s)", to_email, subject)
        return True
    except Exception as exc:
        logger.exception(
            "Échec envoi document (Brevo) → %s | %s: %s",
            to_email,
            type(exc).__name__,
            exc,
        )
        return False


async def send_capcore_contact_email(
    *,
    project_title: str,
    client_name: str,
    client_email: str,
    message: str,
    demo_url: str,
    demo_password: str | None = None,
    unlock_url: str | None = None,
    project_id: str | None = None,
) -> bool:
    """
    Envoie l'email de notification à CapCore via Brevo.
    Retourne False si BREVO_API_KEY absent (log warning) — n'empêche pas l'enregistrement.
    """
    settings = get_settings()
    to_email = (settings.capcore_notify_email or "").strip() or DEFAULT_NOTIFY_EMAIL
    subject, body = _build_contact_email(
        project_title=project_title,
        client_name=client_name,
        client_email=client_email,
        message=message,
        demo_url=demo_url,
        demo_password=demo_password,
        unlock_url=unlock_url,
    )

    if not _brevo_configured():
        logger.warning(
            "Brevo non configuré — email CapCore non envoyé (dest=%s, sujet=%s)",
            to_email,
            subject,
        )
        return False

    try:
        await _send_brevo_email(
            to_email=to_email,
            subject=subject,
            body=body,
            project_id=project_id,
        )
        logger.info("Email CapCore envoyé (Brevo) → %s (%s)", to_email, subject)
        return True
    except Exception as exc:
        logger.exception(
            "Échec envoi email CapCore (Brevo) → %s | %s: %s",
            to_email,
            type(exc).__name__,
            exc,
        )
        return False

