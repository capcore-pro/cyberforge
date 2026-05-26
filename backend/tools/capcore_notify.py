"""
Notification email CapCore — formulaire « Contacter CapCore » sur une démo.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "capcore.pro@gmail.com"


def _smtp_configured() -> bool:
    settings = get_settings()
    return bool(
        plain_secret_str(settings.smtp_user)
        and plain_secret_str(settings.smtp_password)
    )


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


def _send_smtp_sync(
    *,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    settings = get_settings()
    host = settings.smtp_host.strip() or "smtp.gmail.com"
    port = settings.smtp_port
    user = plain_secret_str(settings.smtp_user)
    password = plain_secret_str(settings.smtp_password)
    from_addr = (settings.smtp_from or "").strip() or user
    if not user or not password:
        raise RuntimeError("SMTP non configuré (SMTP_USER / SMTP_PASSWORD).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)


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
    Envoie l'email de notification à CapCore.
    Retourne False si SMTP absent (log warning) — n'empêche pas l'enregistrement.
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

    if not _smtp_configured():
        logger.warning(
            "SMTP non configuré — email CapCore non envoyé (dest=%s, sujet=%s)",
            to_email,
            subject,
        )
        return False

    try:
        await asyncio.to_thread(
            _send_smtp_sync,
            to_email=to_email,
            subject=subject,
            body=body,
        )
        logger.info("Email CapCore envoyé → %s (%s)", to_email, subject)
        return True
    except Exception:
        logger.exception("Échec envoi email CapCore → %s", to_email)
        return False
