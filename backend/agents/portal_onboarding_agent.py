# backend/agents/portal_onboarding_agent.py
# Onboarding Portail Client — création compte + emails + reset password — MAJ62

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import get_settings, plain_secret_str
from utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

PORTAL_URL = os.getenv("PORTAL_URL", "https://client.capcore.pro")
REPLY_TO_EMAIL = "contact@capcore.pro"
REPLY_TO_NAME = "Mat · CapCore Studio Digital"
BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
RESET_TOKEN_EXPIRY_HOURS = 1
MAINTENANCE_PRICE_EUR = 49.00


def _resolve_sender() -> tuple[str, str]:
    settings = get_settings()
    email = (settings.brevo_sender_email or "").strip() or REPLY_TO_EMAIL
    name = (settings.brevo_sender_name or "").strip() or REPLY_TO_NAME
    return email, name


# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────

def _password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _brevo_api_key() -> str:
    return plain_secret_str(get_settings().brevo_api_key) or ""


def _send_brevo_html(
    *,
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    reply_to: dict[str, str] | None = None,
) -> None:
    """Envoie un email HTML via l'API Brevo (httpx)."""
    api_key = _brevo_api_key()
    if not api_key:
        raise RuntimeError("Brevo non configuré (BREVO_API_KEY).")

    sender_email, sender_name = _resolve_sender()
    payload: dict[str, Any] = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if reply_to:
        payload["replyTo"] = reply_to

    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        resp = client.post(
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


def _generate_temp_password() -> str:
    """Génère un mot de passe temporaire sécurisé 12 caractères."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#"
    return "".join(secrets.choice(alphabet) for _ in range(12))


def _generate_reset_token() -> str:
    """Génère un token de reset sécurisé."""
    return secrets.token_urlsafe(32)


# ─────────────────────────────────────────────
# EMAIL BIENVENUE
# ─────────────────────────────────────────────

def send_welcome_email(
    client_email: str,
    client_name: str,
    site_url: str,
    temp_password: str,
    project_name: str = "votre site",
) -> dict[str, Any]:
    """
    Envoie l'email de bienvenue avec identifiants portail.
    Template HTML premium CapCore.
    """
    portal_login_url = f"{PORTAL_URL}/login"

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bienvenue sur votre espace CapCore</title>
</head>
<body style="margin:0;padding:0;background-color:#0f0f13;font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f13;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header avec logo -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);border-radius:16px 16px 0 0;padding:40px 40px 30px;text-align:center;">
              <div style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);border-radius:12px;padding:10px 20px;margin-bottom:20px;">
                <span style="color:#ffffff;font-weight:900;font-size:22px;letter-spacing:2px;">⚡ CAPCORE</span>
              </div>
              <h1 style="color:#ffffff;font-size:28px;font-weight:700;margin:0 0 8px;line-height:1.3;">
                Votre site est en ligne ! 🎉
              </h1>
              <p style="color:#94a3b8;font-size:16px;margin:0;">
                {project_name} est maintenant accessible sur le web
              </p>
            </td>
          </tr>

          <!-- Site preview card -->
          <tr>
            <td style="background:#1e1e2e;padding:0 40px;">
              <div style="background:linear-gradient(135deg,#1e3a5f,#1a2744);border:1px solid #2d4a7a;border-radius:12px;padding:20px 24px;margin:24px 0;text-align:center;">
                <p style="color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px;">Votre site</p>
                <a href="{site_url}" style="color:#60a5fa;font-size:16px;font-weight:600;text-decoration:none;word-break:break-all;">{site_url}</a>
                <div style="margin-top:12px;">
                  <a href="{site_url}" style="display:inline-block;background:#2563eb;color:#ffffff;padding:8px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;">
                    Voir mon site →
                  </a>
                </div>
              </div>
            </td>
          </tr>

          <!-- Identifiants -->
          <tr>
            <td style="background:#1e1e2e;padding:0 40px;">
              <h2 style="color:#f1f5f9;font-size:18px;font-weight:700;margin:0 0 16px;">
                🔑 Vos identifiants de connexion
              </h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:16px 20px;margin-bottom:10px;">
                    <table width="100%">
                      <tr>
                        <td>
                          <p style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:0 0 4px;">Email</p>
                          <p style="color:#e2e8f0;font-size:16px;font-weight:600;margin:0;">{client_email}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr><td style="height:10px;"></td></tr>
                <tr>
                  <td style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:16px 20px;">
                    <p style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:0 0 4px;">Mot de passe temporaire</p>
                    <p style="color:#f59e0b;font-size:20px;font-weight:700;letter-spacing:2px;margin:0;font-family:monospace;">{temp_password}</p>
                    <p style="color:#475569;font-size:12px;margin:6px 0 0;">⚠️ Changez-le dès votre première connexion</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA connexion -->
          <tr>
            <td style="background:#1e1e2e;padding:24px 40px;">
              <div style="text-align:center;">
                <a href="{portal_login_url}" style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);color:#ffffff;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:16px;font-weight:700;letter-spacing:0.5px;">
                  Accéder à mon espace →
                </a>
                <p style="color:#475569;font-size:13px;margin:12px 0 0;">{portal_login_url}</p>
              </div>
            </td>
          </tr>

          <!-- Ce que vous pouvez faire -->
          <tr>
            <td style="background:#1e1e2e;padding:0 40px 24px;">
              <h3 style="color:#f1f5f9;font-size:16px;font-weight:700;margin:0 0 14px;">✨ Ce que vous pouvez faire depuis votre espace :</h3>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:6px 0;">
                    <span style="color:#22c55e;font-weight:700;">✓</span>
                    <span style="color:#94a3b8;font-size:14px;margin-left:8px;">Modifier vos textes et photos en 1 clic</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;">
                    <span style="color:#22c55e;font-weight:700;">✓</span>
                    <span style="color:#94a3b8;font-size:14px;margin-left:8px;">Publier vos changements en ~10 secondes</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;">
                    <span style="color:#22c55e;font-weight:700;">✓</span>
                    <span style="color:#94a3b8;font-size:14px;margin-left:8px;">14 jours d'essai gratuit — sans carte bancaire</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;">
                    <span style="color:#22c55e;font-weight:700;">✓</span>
                    <span style="color:#94a3b8;font-size:14px;margin-left:8px;">Support direct avec Mat si besoin</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#161622;border-radius:0 0 16px 16px;padding:24px 40px;border-top:1px solid #1e293b;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="color:#334155;font-size:13px;margin:0 0 4px;">
                      Une question ? Répondez directement à cet email.
                    </p>
                    <p style="color:#334155;font-size:12px;margin:0;">
                      Mat Gibiard · CapCore Studio Digital · contact@capcore.pro
                    </p>
                  </td>
                  <td align="right">
                    <span style="color:#f59e0b;font-weight:900;font-size:16px;">⚡ CAPCORE</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""

    try:
        _send_brevo_html(
            to_email=client_email,
            to_name=client_name,
            subject="⚡ Votre site est en ligne — Accédez à votre espace CapCore",
            html_content=html_content,
            reply_to={"email": REPLY_TO_EMAIL, "name": REPLY_TO_NAME},
        )

        supabase = get_supabase()
        supabase.table("portal_clients").update({
            "welcome_email_sent_at": datetime.now(timezone.utc).isoformat()
        }).eq("email", client_email).execute()

        return {"sent": True, "to": client_email}
    except Exception as e:
        logger.error("[PortalOnboardingAgent] Erreur email bienvenue: %s", e)
        return {"sent": False, "error": str(e)}


# ─────────────────────────────────────────────
# EMAIL RESET PASSWORD
# ─────────────────────────────────────────────

def send_reset_password_email(client_email: str, client_name: str, reset_token: str) -> dict[str, Any]:
    """Envoie l'email de réinitialisation de mot de passe."""
    reset_url = f"{PORTAL_URL}/reset-password?token={reset_token}"

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#0f0f13;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f13;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);border-radius:16px 16px 0 0;padding:40px;text-align:center;">
              <div style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);border-radius:12px;padding:10px 20px;margin-bottom:20px;">
                <span style="color:#fff;font-weight:900;font-size:22px;letter-spacing:2px;">⚡ CAPCORE</span>
              </div>
              <h1 style="color:#fff;font-size:26px;font-weight:700;margin:0;">Réinitialisation de mot de passe</h1>
            </td>
          </tr>

          <!-- Corps -->
          <tr>
            <td style="background:#1e1e2e;padding:40px;">
              <p style="color:#94a3b8;font-size:16px;margin:0 0 24px;">
                Bonjour {client_name},<br><br>
                Vous avez demandé à réinitialiser votre mot de passe. Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe.
              </p>
              <div style="text-align:center;margin:32px 0;">
                <a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:16px;font-weight:700;">
                  Réinitialiser mon mot de passe →
                </a>
              </div>
              <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:16px;text-align:center;">
                <p style="color:#64748b;font-size:12px;margin:0 0 6px;">Ou copiez ce lien dans votre navigateur :</p>
                <p style="color:#60a5fa;font-size:13px;word-break:break-all;margin:0;">{reset_url}</p>
              </div>
              <p style="color:#475569;font-size:13px;margin:24px 0 0;text-align:center;">
                ⏱️ Ce lien expire dans <strong style="color:#f59e0b;">1 heure</strong>.<br>
                Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#161622;border-radius:0 0 16px 16px;padding:20px 40px;border-top:1px solid #1e293b;">
              <p style="color:#334155;font-size:12px;margin:0;text-align:center;">
                Mat Gibiard · CapCore Studio Digital · contact@capcore.pro
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    try:
        _send_brevo_html(
            to_email=client_email,
            to_name=client_name,
            subject="🔑 Réinitialisation de votre mot de passe CapCore",
            html_content=html_content,
        )
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}


def send_password_changed_email(client_email: str, client_name: str) -> dict[str, Any]:
    """Confirmation que le mot de passe a bien été changé."""
    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#0f0f13;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f13;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);border-radius:16px 16px 0 0;padding:40px;text-align:center;">
              <div style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);border-radius:12px;padding:10px 20px;margin-bottom:20px;">
                <span style="color:#fff;font-weight:900;font-size:22px;letter-spacing:2px;">⚡ CAPCORE</span>
              </div>
              <div style="font-size:48px;margin-bottom:12px;">✅</div>
              <h1 style="color:#fff;font-size:24px;font-weight:700;margin:0;">Mot de passe modifié</h1>
            </td>
          </tr>
          <tr>
            <td style="background:#1e1e2e;padding:40px;text-align:center;">
              <p style="color:#94a3b8;font-size:16px;margin:0 0 24px;">
                Bonjour {client_name},<br><br>
                Votre mot de passe a bien été modifié. Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.
              </p>
              <a href="{PORTAL_URL}/login" style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:16px;font-weight:700;">
                Se connecter →
              </a>
              <p style="color:#475569;font-size:13px;margin:24px 0 0;">
                Si vous n'êtes pas à l'origine de ce changement, contactez-nous immédiatement à contact@capcore.pro
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#161622;border-radius:0 0 16px 16px;padding:20px 40px;border-top:1px solid #1e293b;">
              <p style="color:#334155;font-size:12px;margin:0;text-align:center;">
                Mat Gibiard · CapCore Studio Digital · contact@capcore.pro
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    try:
        _send_brevo_html(
            to_email=client_email,
            to_name=client_name,
            subject="✅ Votre mot de passe CapCore a été modifié",
            html_content=html_content,
        )
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}


# ─────────────────────────────────────────────
# CRÉATION COMPTE PORTAIL
# ─────────────────────────────────────────────

def create_portal_account(
    email: str,
    name: str,
    site_url: str,
    project_name: str,
    send_email: bool = True,
) -> dict[str, Any]:
    """
    Crée un compte portail client avec mot de passe temporaire.
    Envoie l'email de bienvenue si send_email=True.
    Utilisé depuis CyberForge au moment de la livraison.
    """
    supabase = get_supabase()

    existing = supabase.table("portal_clients").select("id, email").eq("email", email).execute()
    if existing.data:
        return {
            "created": False,
            "reason": "already_exists",
            "client_id": existing.data[0]["id"],
            "message": f"Un compte portail existe déjà pour {email}",
        }

    temp_password = _generate_temp_password()
    password_hash = _password_hash(temp_password)

    supabase_user_id: str | None = None
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {"name": name, "role": "portal_client"},
        })
        if auth_response.user:
            supabase_user_id = str(auth_response.user.id)
    except Exception as e:
        return {"created": False, "error": f"Erreur Supabase Auth: {str(e)}"}

    try:
        result = supabase.table("portal_clients").insert({
            "email": email,
            "full_name": name,
            "password_hash": password_hash,
            "supabase_user_id": supabase_user_id,
            "site_url": site_url,
            "plan": "trial",
            "subscription_status": "trial",
            "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
            "onboarding_done": False,
            "management_plan": None,
            "is_active": True,
        }).execute()
    except Exception as e:
        return {"created": False, "error": f"Erreur insertion portal_clients: {str(e)}"}

    client_id = result.data[0]["id"] if result.data else None

    email_result: dict[str, Any] = {"sent": False}
    if send_email:
        email_result = send_welcome_email(
            client_email=email,
            client_name=name,
            site_url=site_url,
            temp_password=temp_password,
            project_name=project_name,
        )

    return {
        "created": True,
        "client_id": client_id,
        "email": email,
        "temp_password": temp_password,
        "email_sent": email_result.get("sent", False),
        "portal_url": f"{PORTAL_URL}/login",
        "trial_days": 14,
    }


# ─────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────

def request_password_reset(email: str) -> dict[str, Any]:
    """
    Génère un token de reset + envoie l'email.
    Toujours retourne succès pour ne pas révéler si l'email existe.
    """
    supabase = get_supabase()

    result = supabase.table("portal_clients").select(
        "id, email, full_name"
    ).eq("email", email).execute()

    if not result.data:
        return {"sent": True, "message": "Si cet email existe, vous recevrez un lien de réinitialisation"}

    client = result.data[0]
    token = _generate_reset_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)).isoformat()

    supabase.table("portal_clients").update({
        "password_reset_token": token,
        "password_reset_expires_at": expires_at,
    }).eq("id", client["id"]).execute()

    send_reset_password_email(
        client_email=client["email"],
        client_name=client.get("full_name") or "",
        reset_token=token,
    )

    return {"sent": True, "message": "Si cet email existe, vous recevrez un lien de réinitialisation"}


def reset_password(token: str, new_password: str) -> dict[str, Any]:
    """Réinitialise le mot de passe avec le token."""
    if len(new_password) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères")

    supabase = get_supabase()

    result = supabase.table("portal_clients").select(
        "id, email, full_name, password_reset_expires_at, supabase_user_id"
    ).eq("password_reset_token", token).execute()

    if not result.data:
        raise ValueError("Token invalide ou expiré")

    client = result.data[0]
    expires_at = client.get("password_reset_expires_at")
    if expires_at:
        exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp_dt:
            raise ValueError("Token expiré — veuillez refaire une demande")

    new_hash = _password_hash(new_password)

    auth_user_id = client.get("supabase_user_id") or client["id"]
    try:
        supabase.auth.admin.update_user_by_id(
            auth_user_id,
            {"password": new_password},
        )
    except Exception as e:
        raise ValueError(f"Erreur mise à jour mot de passe: {str(e)}") from e

    supabase.table("portal_clients").update({
        "password_hash": new_hash,
        "password_reset_token": None,
        "password_reset_expires_at": None,
    }).eq("id", client["id"]).execute()

    send_password_changed_email(
        client["email"],
        client.get("full_name") or "",
    )

    return {"success": True, "email": client["email"]}


def mark_onboarding_done(client_id: str, management_plan: str) -> dict[str, Any]:
    """Marque l'onboarding comme terminé avec le plan choisi."""
    if management_plan not in ("autonome", "gere"):
        raise ValueError("Plan invalide — autonome ou gere")

    supabase = get_supabase()
    supabase.table("portal_clients").update({
        "onboarding_done": True,
        "management_plan": management_plan,
        "first_login_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", client_id).execute()

    if management_plan == "gere":
        supabase.table("portal_management_plans").insert({
            "client_id": client_id,
            "plan_type": "gere",
            "price_eur": MAINTENANCE_PRICE_EUR,
            "modifications_per_month": 2,
            "status": "active",
        }).execute()

    return {"success": True, "management_plan": management_plan}


def notify_portal_client_site_updated(project_id: str, live_url: str) -> bool:
    """
    Envoie l'email de confirmation MAJ site au client portail si un compte est lié.
    Non bloquant pour l'appelant — les erreurs doivent être catchées en amont.
    """
    supabase = get_supabase()

    site_row = (
        supabase.table("portal_sites")
        .select("id, client_id, site_url")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )

    client_id: str | None = None
    if site_row.data:
        client_id = site_row.data[0]["client_id"]
    else:
        client_row = (
            supabase.table("portal_clients")
            .select("id")
            .eq("site_url", live_url)
            .limit(1)
            .execute()
        )
        if client_row.data:
            client_id = client_row.data[0]["id"]

    if not client_id:
        return False

    client_info = (
        supabase.table("portal_clients")
        .select("email, full_name")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )

    if not client_info.data:
        return False

    onboarding_agent = PortalOnboardingAgent()
    return onboarding_agent.send_site_modification_email(
        client_email=client_info.data[0]["email"],
        client_name=client_info.data[0].get("full_name") or "",
        site_url=live_url,
    )


class PortalOnboardingAgent:
    """Façade classe pour emails onboarding (évite imports circulaires depuis portal_agent)."""

    def send_site_modification_email(
        self, client_email: str, client_name: str, site_url: str
    ) -> bool:
        """Envoie un email de confirmation après modification du site par le client."""
        now = datetime.now().strftime("%d/%m/%Y à %H:%M")

        html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Modifications enregistrées</title>
</head>
<body style="margin:0;padding:0;background-color:#0f0f13;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f13;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:40px 40px 30px;border-radius:12px 12px 0 0;text-align:center;">
              <div style="font-size:28px;font-weight:900;letter-spacing:2px;color:#f59e0b;">
                ⚡ CAPCORE
              </div>
              <div style="color:#94a3b8;font-size:12px;letter-spacing:3px;margin-top:4px;">
                STUDIO DIGITAL
              </div>
            </td>
          </tr>

          <tr>
            <td style="background-color:#1a1a2e;padding:40px;">

              <div style="text-align:center;margin-bottom:24px;">
                <div style="display:inline-block;width:64px;height:64px;background:linear-gradient(135deg,#065f46,#047857);border-radius:50%;line-height:64px;font-size:28px;">
                  ✅
                </div>
              </div>

              <h1 style="color:#f1f5f9;font-size:22px;font-weight:700;text-align:center;margin:0 0 8px;">
                Modifications enregistrées
              </h1>
              <p style="color:#94a3b8;font-size:14px;text-align:center;margin:0 0 32px;">
                Le {now}
              </p>

              <p style="color:#cbd5e1;font-size:15px;line-height:1.6;margin:0 0 16px;">
                Bonjour {client_name},
              </p>
              <p style="color:#cbd5e1;font-size:15px;line-height:1.6;margin:0 0 32px;">
                Vos modifications ont bien été enregistrées et <strong style="color:#f1f5f9;">mises en ligne sur votre site</strong>. Les changements sont visibles immédiatement.
              </p>

              <div style="text-align:center;margin:0 0 32px;">
                <a href="{site_url}" target="_blank"
                   style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);color:#0f0f13;font-weight:700;font-size:15px;padding:14px 36px;border-radius:8px;text-decoration:none;letter-spacing:0.5px;">
                  Voir mon site →
                </a>
              </div>

              <div style="background-color:#0f0f13;border:1px solid #374151;border-left:4px solid #3b82f6;border-radius:8px;padding:16px 20px;margin:0 0 24px;">
                <p style="color:#94a3b8;font-size:13px;margin:0 0 4px;">Site mis à jour</p>
                <a href="{site_url}" style="color:#60a5fa;font-size:14px;text-decoration:none;word-break:break-all;">{site_url}</a>
              </div>

              <p style="color:#64748b;font-size:13px;line-height:1.6;margin:0;">
                Si vous n'êtes pas à l'origine de ces modifications ou si vous constatez un problème, contactez-nous immédiatement en répondant à cet email.
              </p>

            </td>
          </tr>

          <tr>
            <td style="background-color:#0f0f13;padding:24px 40px;border-radius:0 0 12px 12px;border-top:1px solid #1e293b;text-align:center;">
              <p style="color:#475569;font-size:12px;margin:0 0 4px;">
                Mat · CapCore Studio Digital
              </p>
              <p style="color:#334155;font-size:11px;margin:0;">
                Votre partenaire digital
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        try:
            _send_brevo_html(
                to_email=client_email,
                to_name=client_name,
                subject="✅ Vos modifications sont en ligne — CapCore",
                html_content=html_content,
                reply_to={"email": REPLY_TO_EMAIL, "name": REPLY_TO_NAME},
            )
            return True
        except Exception as e:
            logger.error(
                "[PortalOnboardingAgent] Erreur email confirmation modification: %s", e
            )
            return False

    def send_delegation_request_email(
        self,
        client_email: str,
        client_name: str,
        site_url: str,
        site_name: str,
    ) -> bool:
        """Email à Mat quand un client demande la gestion déléguée."""
        mat_email = "mat@capcore.fr"
        html = f"""
    <div style="background:#0f0f13;padding:40px;font-family:Arial,sans-serif;color:#fff;">
      <h2 style="color:#00d4ff;">🔔 Nouvelle demande de gestion déléguée</h2>
      <p style="color:#ccc;">Un client souhaite déléguer la gestion de son site à CapCore.</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr><td style="padding:8px;color:#888;">Client</td><td style="padding:8px;color:#fff;">{client_name}</td></tr>
        <tr><td style="padding:8px;color:#888;">Email</td><td style="padding:8px;color:#00d4ff;">{client_email}</td></tr>
        <tr><td style="padding:8px;color:#888;">Site</td><td style="padding:8px;color:#fff;">{site_name}</td></tr>
        <tr><td style="padding:8px;color:#888;">URL</td><td style="padding:8px;color:#00d4ff;">{site_url}</td></tr>
      </table>
      <p style="color:#888;">L'abonnement Stripe du client a été annulé automatiquement.</p>
      <p style="color:#888;">Pense à configurer la facturation 49€/mois pour ce client.</p>
    </div>
    """
        try:
            _send_brevo_html(
                to_email=mat_email,
                to_name="Mat — CapCore",
                subject=f"🔔 Délégation demandée — {client_name} ({site_name})",
                html_content=html,
            )
            return True
        except Exception as e:
            logger.error(
                "[PortalOnboardingAgent] Erreur email demande délégation: %s", e
            )
            return False

    def send_delegation_confirmation_email(
        self,
        client_email: str,
        client_name: str,
        site_name: str,
    ) -> bool:
        """Email au client confirmant la prise en charge par CapCore."""
        html = f"""
    <div style="background:#0f0f13;padding:40px;font-family:Arial,sans-serif;color:#fff;">
      <h2 style="color:#00d4ff;">✅ CapCore prend en charge votre site</h2>
      <p style="color:#ccc;">Bonjour {client_name},</p>
      <p style="color:#ccc;">Votre demande a bien été reçue. CapCore Studio Digital gère désormais votre site <strong style="color:#fff;">{site_name}</strong>.</p>
      <p style="color:#ccc;">Mat prendra contact avec vous très prochainement pour convenir des premières modifications.</p>
      <div style="background:#1a1a2e;border-radius:8px;padding:20px;margin:20px 0;">
        <p style="color:#00d4ff;margin:0;">📋 Pour demander des modifications</p>
        <p style="color:#888;margin:8px 0 0;">Connectez-vous à votre espace client et utilisez le formulaire "Demander une modification".</p>
      </div>
    </div>
    """
        try:
            _send_brevo_html(
                to_email=client_email,
                to_name=client_name,
                subject=f"✅ CapCore prend en charge {site_name}",
                html_content=html,
            )
            return True
        except Exception as e:
            logger.error(
                "[PortalOnboardingAgent] Erreur email confirmation délégation: %s", e
            )
            return False

    def send_back_to_autonome_email(
        self,
        client_email: str,
        client_name: str,
        site_name: str,
        pricing_url: str = "https://client.capcore.pro/pricing",
    ) -> bool:
        """Email au client quand Mat le repasse en mode autonome."""
        html = f"""
    <div style="background:#0f0f13;padding:40px;font-family:Arial,sans-serif;color:#fff;">
      <h2 style="color:#00d4ff;">🔄 Votre site est prêt pour une gestion autonome</h2>
      <p style="color:#ccc;">Bonjour {client_name},</p>
      <p style="color:#ccc;">Votre site <strong style="color:#fff;">{site_name}</strong> est désormais disponible en gestion autonome.</p>
      <p style="color:#ccc;">Choisissez votre plan pour accéder à l'éditeur et modifier votre site en toute autonomie :</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="{pricing_url}" style="background:#00d4ff;color:#000;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;">
          Choisir mon plan →
        </a>
      </div>
    </div>
    """
        try:
            _send_brevo_html(
                to_email=client_email,
                to_name=client_name,
                subject=f"🔄 Choisissez votre plan — {site_name}",
                html_content=html,
            )
            return True
        except Exception as e:
            logger.error(
                "[PortalOnboardingAgent] Erreur email retour autonome: %s", e
            )
            return False

    def send_modification_request_email(
        self,
        client_email: str,
        client_name: str,
        site_name: str,
        site_url: str,
        type_modification: str,
        description: str,
        priorite: str,
        fichiers_joints: list[str] | None = None,
    ) -> bool:
        """Email à Mat avec la demande de modification du client géré."""
        mat_email = "mat@capcore.fr"
        fichiers_html = ""
        if fichiers_joints:
            fichiers_html = "<p style='color:#888;'>Fichiers joints :</p><ul>"
            for f in fichiers_joints:
                fichiers_html += f"<li style='color:#00d4ff;'>{f}</li>"
            fichiers_html += "</ul>"

        priorite_color = "#ff4444" if priorite == "urgente" else "#00d4ff"
        html = f"""
    <div style="background:#0f0f13;padding:40px;font-family:Arial,sans-serif;color:#fff;">
      <h2 style="color:#00d4ff;">📝 Demande de modification — {site_name}</h2>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr><td style="padding:8px;color:#888;">Client</td><td style="padding:8px;color:#fff;">{client_name} ({client_email})</td></tr>
        <tr><td style="padding:8px;color:#888;">Site</td><td style="padding:8px;color:#fff;">{site_name}</td></tr>
        <tr><td style="padding:8px;color:#888;">URL</td><td style="padding:8px;color:#00d4ff;">{site_url}</td></tr>
        <tr><td style="padding:8px;color:#888;">Type</td><td style="padding:8px;color:#fff;">{type_modification}</td></tr>
        <tr><td style="padding:8px;color:#888;">Priorité</td><td style="padding:8px;color:{priorite_color};font-weight:bold;">{priorite.upper()}</td></tr>
      </table>
      <div style="background:#1a1a2e;border-radius:8px;padding:20px;margin:20px 0;">
        <p style="color:#888;margin:0 0 8px;">Description :</p>
        <p style="color:#fff;margin:0;">{description}</p>
      </div>
      {fichiers_html}
    </div>
    """
        try:
            _send_brevo_html(
                to_email=mat_email,
                to_name="Mat — CapCore",
                subject=f"📝 Modif demandée — {client_name} — {site_name} [{priorite.upper()}]",
                html_content=html,
            )
            return True
        except Exception as e:
            logger.error(
                "[PortalOnboardingAgent] Erreur email demande modification: %s", e
            )
            return False
