"""
Prévisualisation démo — sans écran de connexion (gate réservé à l'export final).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Bypass mot de passe pour Mat dans CyberForge (pas pour liens clients partagés).
CYBERFORGE_INTERNAL_PREVIEW_QUERY = "preview"
CYBERFORGE_INTERNAL_PREVIEW_VALUE = "cyberforge_internal"


def is_password_gated(html: str) -> bool:
    low = (html or "").lower()
    return "cf-login-screen" in low and "cf-demo-content" in low


def strip_password_gate(html: str) -> str:
    """
    Retire l'enveloppe « Démo protégée » et ne garde que le livrable client.
    """
    if not html or not is_password_gated(html):
        return html

    start_m = re.search(
        r'<div[^>]+id=["\']cf-demo-content["\'][^>]*>',
        html,
        re.I,
    )
    if not start_m:
        return html

    inner_start = start_m.end()
    body_end = re.search(r"</body>", html[inner_start:], re.I)
    if not body_end:
        return html

    inner = html[inner_start : inner_start + body_end.start()].strip()
    inner = re.sub(r"^```html\s*", "", inner, flags=re.I)
    inner = re.sub(r"```\s*$", "", inner, flags=re.I)

    title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    title = (title_m.group(1) if title_m else "Site vitrine").strip()

    if len(inner) < 120:
        return html

    if re.search(r"<!DOCTYPE|<html", inner, re.I):
        return inner

    return (
        f"<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
        f'<meta charset="UTF-8" />\n<title>{title}</title>\n</head>\n'
        f"<body>\n{inner}\n</body>\n</html>"
    )


def append_cyberforge_internal_preview_query(url: str) -> str:
    """Ajoute ?preview=cyberforge_internal pour ouverture interne CyberForge."""
    raw = (url or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    if not parsed.scheme.startswith("http"):
        return raw
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if params.get(CYBERFORGE_INTERNAL_PREVIEW_QUERY) == CYBERFORGE_INTERNAL_PREVIEW_VALUE:
        return raw
    params[CYBERFORGE_INTERNAL_PREVIEW_QUERY] = CYBERFORGE_INTERNAL_PREVIEW_VALUE
    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))


def prepare_internal_app_preview_html(html: str) -> str:
    """Aperçu in-app (iframe srcDoc) — jamais l'écran « Démo protégée »."""
    raw = (html or "").strip()
    if not raw or not is_password_gated(raw):
        return raw
    stripped = strip_password_gate(raw)
    if not is_password_gated(stripped):
        return stripped
    from tools.vitrine_html_normalize import extract_unlocked_demo_html

    return extract_unlocked_demo_html(raw)
