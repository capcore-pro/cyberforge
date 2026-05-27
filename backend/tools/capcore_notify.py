"""
Notification email CapCore — formulaire « Contacter CapCore » sur une démo (API Brevo).
"""

from __future__ import annotations

import logging

import httpx

from config import get_settings, plain_secret_str

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


async def _send_brevo_email(*, to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    api_key = plain_secret_str(settings.brevo_api_key)
    if not api_key:
        raise RuntimeError("Brevo non configuré (BREVO_API_KEY).")

    sender_name, sender_email = _resolve_sender()
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

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


async def send_capcore_contact_email(
    *,
    project_title: str,
    client_name: str,
    client_email: str,
    message: str,
    demo_url: str,
    demo_password: str | None = None,
    unlock_url: str | None = None,
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
        await _send_brevo_email(to_email=to_email, subject=subject, body=body)
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
