"""
EmailAI — notifications transactionnelles Brevo (déploiement, commande, réservation).
"""

from __future__ import annotations

import html
import logging
from typing import Any

from config import get_settings
from tools.capcore_notify import _brevo_configured, send_html_email

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "capcore.pro@gmail.com"

_PROJECT_TYPE_LABELS: dict[str, str] = {
    "vitrine_next": "Vitrine",
    "vitrine": "Vitrine",
    "ecommerce": "E-commerce",
    "site_reservation": "Réservation",
    "application_web": "App web",
    "real_app": "App web",
    "extension_navigateur": "Extension",
    "application_desktop": "App desktop",
    "saas_dashboard": "SaaS dashboard",
}


def _esc(value: Any) -> str:
    return html.escape(str(value or "").strip())


def _format_duration_ms(duration_ms: int | float | None) -> str:
    total_sec = max(0, int((duration_ms or 0) / 1000))
    minutes, seconds = divmod(total_sec, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _project_type_label(project_type: str | None) -> str:
    key = (project_type or "").strip().lower().replace("-", "_")
    return _PROJECT_TYPE_LABELS.get(key, key or "Projet")


def _format_money(amount: float | int, currency: str = "eur") -> str:
    cur = (currency or "eur").upper()
    symbol = "€" if cur == "EUR" else f" {cur}"
    value = float(amount)
    if value == int(value):
        return f"{int(value)}{symbol}"
    return f"{value:.2f}{symbol}"


def _build_email_html(
    *,
    header_color: str,
    header_title: str,
    header_subtitle: str,
    body_rows: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    footer_url: str | None = None,
    preview_line: str | None = None,
) -> str:
    """Template email 600px — tables HTML, compatible clients mail."""
    primary = _esc(header_color or "#6366f1")
    title = _esc(header_title)
    subtitle = _esc(header_subtitle)
    footer_link = _esc(footer_url or "")
    preheader = (
        f'<div style="display:none;max-height:0;overflow:hidden;">{_esc(preview_line)}</div>'
        if preview_line
        else ""
    )
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
          <tr>
            <td align="center" style="padding:24px 32px 8px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" bgcolor="{primary}" style="border-radius:8px;">
                    <a href="{_esc(cta_url)}" target="_blank"
                       style="display:inline-block;padding:14px 28px;font-family:Segoe UI,Helvetica,Arial,sans-serif;
                       font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">
                      {_esc(cta_label)}
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""

    footer_href = f'<a href="{footer_link}" style="color:#8892a4;text-decoration:underline;">{footer_link}</a>' if footer_link else ""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background-color:#0f1117;">
{preheader}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0f1117;">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">
        <tr>
          <td bgcolor="{primary}" style="padding:28px 32px;border-radius:12px 12px 0 0;">
            <p style="margin:0;font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:22px;font-weight:700;color:#ffffff;">{title}</p>
            <p style="margin:8px 0 0;font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:14px;color:rgba(255,255,255,0.9);">{subtitle}</p>
          </td>
        </tr>
        <tr>
          <td bgcolor="#1e2535" style="padding:0;border-radius:0 0 12px 12px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              {body_rows}
              {cta_block}
              <tr>
                <td style="padding:24px 32px 28px;font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:12px;color:#8892a4;line-height:1.6;">
                  CyberForge — Généré par CapCore<br/>
                  {footer_href}
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
</html>"""


def _body_paragraph(text: str, *, bold: bool = False) -> str:
    weight = "font-weight:600;" if bold else ""
    return f"""
          <tr>
            <td style="padding:20px 32px 0;font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#e2e8f0;{weight}">
              {_esc(text)}
            </td>
          </tr>"""


def _body_html_block(inner_html: str) -> str:
    return f"""
          <tr>
            <td style="padding:20px 32px 0;font-family:Segoe UI,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#e2e8f0;">
              {inner_html}
            </td>
          </tr>"""


async def send_deployment_notification(
    *,
    brief: dict[str, Any],
    demo_url: str,
    duration_ms: int | float | None = None,
) -> bool:
    """Notifie Mat (capcore_notify_email) qu'un site vient d'être déployé."""
    if not _brevo_configured():
        logger.warning(
            "[EmailAI] Brevo non configuré — notification déploiement ignorée"
        )
        return False

    settings = get_settings()
    to_email = (settings.capcore_notify_email or "").strip() or DEFAULT_NOTIFY_EMAIL
    b = brief or {}
    client_name = str(b.get("client_name") or "Client").strip() or "Client"
    project_type = str(b.get("project_type") or "vitrine_next")
    sector = str(b.get("sector") or "—").strip() or "—"
    couleur = str(b.get("couleur_primaire") or "#6366f1").strip()
    ds = b.get("design_system") if isinstance(b.get("design_system"), dict) else {}
    style_family = str(ds.get("style_family") or "—")
    ds_primary = ""
    colors = ds.get("colors") if isinstance(ds.get("colors"), dict) else {}
    if colors:
        ds_primary = str(colors.get("primary") or "")

    pt_label = _project_type_label(project_type)
    subject = f"🚀 {client_name} — {pt_label} déployé"
    duration_label = _format_duration_ms(duration_ms)
    design_line = f"{style_family}"
    if ds_primary:
        design_line += f" · {ds_primary}"
    elif couleur:
        design_line += f" · {couleur}"

    body_rows = (
        _body_paragraph(f"Client : {client_name}", bold=True)
        + _body_paragraph(f"Type : {pt_label}")
        + _body_paragraph(f"Secteur : {sector}")
        + _body_paragraph(f"Durée de génération : {duration_label}")
        + _body_paragraph(f"Design system : {design_line}")
    )
    html_content = _build_email_html(
        header_color=couleur,
        header_title=client_name,
        header_subtitle=f"{pt_label} déployé avec succès",
        body_rows=body_rows,
        cta_label="Voir la démo",
        cta_url=demo_url,
        footer_url=demo_url,
        preview_line=f"{client_name} — {pt_label} en ligne",
    )

    try:
        await send_html_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=(
                f"{client_name} — {pt_label} déployé\n"
                f"URL : {demo_url}\n"
                f"Durée : {duration_label}\n"
                f"Design : {design_line}"
            ),
        )
        logger.info("[EmailAI] Notification déploiement envoyée → %s", to_email)
        return True
    except Exception as exc:
        logger.warning(
            "[EmailAI] Échec notification déploiement → %s | %s",
            to_email,
            exc,
        )
        return False


async def send_order_confirmation(
    *,
    order_data: dict[str, Any],
    shop_name: str,
    shop_url: str,
    couleur_primaire: str = "#d4a843",
    customer_email: str | None = None,
) -> bool:
    """Confirme une commande e-commerce au client."""
    if not _brevo_configured():
        logger.warning(
            "[EmailAI] Brevo non configuré — confirmation commande ignorée"
        )
        return False

    to_email = (customer_email or order_data.get("customer_email") or "").strip()
    if not to_email:
        logger.warning("[EmailAI] customer_email absent — confirmation commande ignorée")
        return False

    items = order_data.get("items") or []
    currency = str(order_data.get("currency") or "eur")
    total = float(order_data.get("total") or 0)
    shop = str(shop_name or "Boutique").strip() or "Boutique"
    subject = f"✅ Commande confirmée — {shop}"

    rows_html = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _esc(item.get("name") or item.get("description") or "Article")
        qty = int(item.get("quantity") or item.get("qty") or 1)
        unit = item.get("unit_amount") or item.get("price") or 0
        if isinstance(unit, (int, float)) and unit > 100:
            unit = float(unit) / 100.0
        line_total = float(unit) * qty
        rows_html += (
            f"<tr>"
            f'<td style="padding:8px 0;border-bottom:1px solid #2d3748;color:#e2e8f0;">{name}</td>'
            f'<td align="center" style="padding:8px 0;border-bottom:1px solid #2d3748;color:#e2e8f0;">{qty}</td>'
            f'<td align="right" style="padding:8px 0;border-bottom:1px solid #2d3748;color:#e2e8f0;">{_format_money(line_total, currency)}</td>'
            f"</tr>"
        )

    items_table = f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;">
        <tr>
          <th align="left" style="padding:8px 0;color:#8892a4;font-size:13px;">Produit</th>
          <th align="center" style="padding:8px 0;color:#8892a4;font-size:13px;">Qté</th>
          <th align="right" style="padding:8px 0;color:#8892a4;font-size:13px;">Prix</th>
        </tr>
        {rows_html}
        <tr>
          <td colspan="2" align="right" style="padding:12px 0 0;color:#e2e8f0;font-weight:600;">Total TTC</td>
          <td align="right" style="padding:12px 0 0;color:#e2e8f0;font-weight:600;">{_format_money(total, currency)}</td>
        </tr>
      </table>"""

    body_rows = (
        _body_paragraph(f"Merci pour votre commande chez {shop} !")
        + _body_html_block(items_table)
        + _body_paragraph("Vous recevrez votre commande sous 3-5 jours ouvrés.")
    )
    html_content = _build_email_html(
        header_color=couleur_primaire,
        header_title=shop,
        header_subtitle="Commande confirmée",
        body_rows=body_rows,
        cta_label="Retourner à la boutique",
        cta_url=shop_url,
        footer_url=shop_url,
        preview_line=f"Commande confirmée — {shop}",
    )

    try:
        await send_html_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            to_name=shop,
            text_content=f"Commande confirmée chez {shop}. Total : {_format_money(total, currency)}",
        )
        logger.info("[EmailAI] Confirmation commande envoyée → %s", to_email)
        return True
    except Exception as exc:
        logger.warning(
            "[EmailAI] Échec confirmation commande → %s | %s",
            to_email,
            exc,
        )
        return False


async def send_reservation_confirmation(
    *,
    reservation_data: dict[str, Any],
    property_name: str,
    property_url: str,
    couleur_primaire: str = "#1D9E75",
) -> bool:
    """Confirme une réservation au client."""
    if not _brevo_configured():
        logger.warning(
            "[EmailAI] Brevo non configuré — confirmation réservation ignorée"
        )
        return False

    to_email = str(reservation_data.get("guest_email") or "").strip()
    if not to_email:
        logger.warning("[EmailAI] guest_email absent — confirmation réservation ignorée")
        return False

    guest_name = str(reservation_data.get("guest_name") or "Client").strip()
    checkin = str(reservation_data.get("checkin") or "—")
    checkout = str(reservation_data.get("checkout") or "—")
    nights = reservation_data.get("nights")
    nights_label = str(nights) if nights is not None else "—"
    total_price = reservation_data.get("total_price")
    price_label = (
        _format_money(float(total_price), "eur")
        if total_price is not None
        else "—"
    )
    contact = str(reservation_data.get("property_contact") or "").strip()
    prop = str(property_name or "Hébergement").strip() or "Hébergement"
    subject = f"📅 Réservation confirmée — {prop}"

    body_rows = (
        _body_paragraph(f"Bonjour {guest_name},", bold=True)
        + _body_paragraph(f"Votre réservation chez {prop} est confirmée.")
        + _body_paragraph(f"Arrivée : {checkin}")
        + _body_paragraph(f"Départ : {checkout}")
        + _body_paragraph(f"Nombre de nuits : {nights_label}")
        + _body_paragraph(f"Montant total : {price_label}")
        + (
            _body_paragraph(f"Pour toute question : {contact}")
            if contact
            else ""
        )
    )
    html_content = _build_email_html(
        header_color=couleur_primaire,
        header_title=prop,
        header_subtitle="Réservation confirmée",
        body_rows=body_rows,
        cta_label="Voir ma réservation",
        cta_url=property_url,
        footer_url=property_url,
        preview_line=f"Réservation confirmée — {prop}",
    )

    try:
        await send_html_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            to_name=guest_name,
            text_content=(
                f"Réservation confirmée — {prop}\n"
                f"{checkin} → {checkout}\n"
                f"Total : {price_label}"
            ),
        )
        logger.info("[EmailAI] Confirmation réservation envoyée → %s", to_email)
        return True
    except Exception as exc:
        logger.warning(
            "[EmailAI] Échec confirmation réservation → %s | %s",
            to_email,
            exc,
        )
        return False


async def notify_client_review_response(
    *,
    project_title: str,
    client_name: str,
    status: str,
    feedback: str | None,
    rating: int | None,
    demo_url: str,
) -> bool:
    """Notifie Mat qu'un client a approuvé ou demandé des révisions."""
    if not _brevo_configured():
        logger.warning(
            "[EmailAI] Brevo non configuré — notification review client ignorée"
        )
        return False

    settings = get_settings()
    to_email = (settings.capcore_notify_email or "").strip() or DEFAULT_NOTIFY_EMAIL
    approved = status == "approved"
    header_color = "#22c55e" if approved else "#f59e0b"
    header_title = "Client a approuvé le site" if approved else "Révisions demandées"
    stars = "⭐" * int(rating) if rating else "—"
    rows = (
        _body_paragraph(f"Projet : {project_title}", bold=True)
        + _body_paragraph(f"Client : {client_name}")
        + _body_paragraph(f"Note : {stars}")
        + _body_paragraph(f"Statut : {'Approuvé' if approved else 'Révisions demandées'}")
    )
    if feedback and feedback.strip():
        rows += _body_paragraph(f"Commentaire : {feedback.strip()}")

    html = _build_email_html(
        header_color=header_color,
        header_title=header_title,
        header_subtitle=project_title,
        body_rows=rows,
        cta_label="Voir la démo" if demo_url else None,
        cta_url=demo_url or None,
        footer_url=demo_url or None,
        preview_line=header_title,
    )
    subject = f"{'✓' if approved else '↩'} Review client — {project_title}"
    try:
        await send_html_email(
            to_email=to_email,
            subject=subject,
            html_content=html,
            to_name="Mat Gibiard",
        )
        logger.info("[EmailAI] Notification review client envoyée → %s", to_email)
        return True
    except Exception as exc:
        logger.warning("[EmailAI] Échec notification review client: %s", exc)
        return False
