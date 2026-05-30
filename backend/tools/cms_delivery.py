"""Contenu email de livraison — lien d'accès CMS client."""

from __future__ import annotations

import html


def append_cms_link_to_email_html(html_body: str, cms_login_url: str | None) -> str:
    """Ajoute le bloc lien d'édition CMS en fin d'email de livraison."""
    url = (cms_login_url or "").strip()
    if not url:
        return html_body
    safe_url = html.escape(url, quote=True)
    block = (
        '<p style="margin-top:20px;padding:14px 16px;background:#f8fafc;'
        'border-left:4px solid #d4af37;border-radius:6px;font-size:15px;line-height:1.5;">'
        "<strong>Modifier votre site vous-même</strong> — connectez-vous à votre espace "
        f'd\'édition : <a href="{safe_url}" style="color:#0284c7;font-weight:600;">'
        f"{safe_url}</a> (utilisez l’email et le mot de passe reçus pour ce projet).</p>"
    )
    body = (html_body or "").strip()
    return f"{body}\n{block}" if body else block
