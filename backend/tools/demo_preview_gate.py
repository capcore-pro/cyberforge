"""
Prévisualisation démo — sans écran de connexion (gate réservé à l'export final).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Bypass mot de passe pour Mat dans CyberForge (pas pour liens clients partagés).
CYBERFORGE_INTERNAL_PREVIEW_QUERY = "preview"
CYBERFORGE_INTERNAL_PREVIEW_VALUE = "cyberforge_internal"


_INTERNAL_PREVIEW_HIDE_LOCK_CSS = (
    '<style id="cf-internal-preview-chrome">'
    "#cf-lock-btn,.cf-lock-btn{display:none!important;visibility:hidden!important;"
    "pointer-events:none!important;height:0!important;overflow:hidden!important}"
    "</style>"
)


def strip_internal_preview_chrome(html: str) -> str:
    """Retire le bouton Verrouiller (réservé aux liens client livrés)."""
    if not html:
        return html
    out = re.sub(
        r'<button\b[^>]*\bid\s*=\s*["\']?cf-lock-btn["\']?[^>]*>[\s\S]*?</button>',
        "",
        html,
        flags=re.I,
    )
    out = re.sub(
        r'<button\b[^>]*\bclass\s*=\s*["\'][^"\']*\bcf-lock-btn\b[^"\']*["\'][^>]*>'
        r"[\s\S]*?</button>",
        "",
        out,
        flags=re.I,
    )
    out = re.sub(
        r"#cf-demo-content\.cf-unlocked\s+\.cf-lock-btn\s*\{[^}]*\}",
        "",
        out,
        flags=re.I,
    )
    out = re.sub(
        r"\.cf-lock-btn\s*\{[^}]*\}",
        "",
        out,
        count=1,
        flags=re.I,
    )
    if 'id="cf-internal-preview-chrome"' not in out:
        if re.search(r"</head>", out, re.I):
            out = re.sub(
                r"(</head>)",
                _INTERNAL_PREVIEW_HIDE_LOCK_CSS + r"\1",
                out,
                count=1,
                flags=re.I,
            )
        elif re.search(r"<body[^>]*>", out, re.I):
            out = re.sub(
                r"(<body[^>]*>)",
                r"\1" + _INTERNAL_PREVIEW_HIDE_LOCK_CSS,
                out,
                count=1,
                flags=re.I,
            )
        else:
            out = _INTERNAL_PREVIEW_HIDE_LOCK_CSS + out
    return out


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
    inner = strip_internal_preview_chrome(inner)
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


def inject_internal_preview_meta(html: str) -> str:
    """Marqueur pour unlockDemo() dans les pages gate (fichier local sans query string)."""
    if not html or 'name="cf-cyberforge-internal-preview"' in html:
        return html
    tag = '<meta name="cf-cyberforge-internal-preview" content="1" />'
    if re.search(r"<head\b", html, re.I):
        return re.sub(r"(<head[^>]*>)", r"\1\n" + tag, html, count=1, flags=re.I)
    return tag + html


def prepare_internal_app_preview_html(html: str) -> str:
    """Aperçu in-app (iframe srcDoc) — jamais l'écran « Démo protégée » ni Verrouiller."""
    raw = (html or "").strip()
    if not raw:
        return raw
    if is_password_gated(raw):
        stripped = strip_password_gate(raw)
        if not is_password_gated(stripped):
            return strip_internal_preview_chrome(stripped)
        from tools.vitrine_html_normalize import extract_unlocked_demo_html

        return strip_internal_preview_chrome(extract_unlocked_demo_html(raw))
    return strip_internal_preview_chrome(raw)
