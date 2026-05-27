"""Config runtime injectée dans les démos Cloudflare (token, API, URL publique)."""

from __future__ import annotations

import json
import re

_RUNTIME_SCRIPT_FULL_RE = re.compile(
    r'<script\s+id="cf-demo-runtime"\s+type="application/json">\s*.*?\s*</script>',
    re.IGNORECASE | re.DOTALL,
)
_BODY_OPEN_RE = re.compile(r"<body(\s[^>]*)?>", re.IGNORECASE)


def resolve_demo_api_base_url(explicit: str = "") -> str:
    """URL backend pour les fetch depuis une démo hébergée sur Cloudflare Pages."""
    clean = explicit.strip().rstrip("/")
    if clean:
        return clean
    from config import get_settings

    return get_settings().demo_api_base_url.strip().rstrip("/")


def extract_demo_title_from_html(html: str) -> str:
    """Titre affiché dans le runtime (balise <title> ou défaut)."""
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        if title and title.lower() not in ("démo", "demo"):
            return title
    return "Démo"


def _read_runtime_payload(html: str) -> dict[str, str] | None:
    match = _RUNTIME_SCRIPT_FULL_RE.search(html)
    if not match:
        return None
    inner = match.group(0)
    start = inner.find(">") + 1
    end = inner.rfind("</script>")
    if start <= 0 or end <= start:
        return None
    try:
        raw = json.loads(inner[start:end].strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return {str(k): str(v) if v is not None else "" for k, v in raw.items()}


def _runtime_script_tag(payload: dict[str, str]) -> str:
    blob = json.dumps(payload, ensure_ascii=False)
    blob = blob.replace("</", "<\\/")
    return f'<script id="cf-demo-runtime" type="application/json">{blob}</script>'


def _strip_runtime_script(html: str) -> str:
    return _RUNTIME_SCRIPT_FULL_RE.sub("", html, count=1)


def _insert_runtime_after_body_open(html: str, script: str) -> str:
    """Place le runtime avant les scripts inline (premium lit apiBase au chargement)."""
    match = _BODY_OPEN_RE.search(html)
    if match:
        pos = match.end()
        return html[:pos] + "\n" + script + html[pos:]
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx >= 0:
        return html[:idx] + script + "\n" + html[idx:]
    return html + script


def ensure_demo_runtime_config(
    html: str,
    *,
    token: str,
    project_title: str = "Démo",
    demo_url: str = "",
    api_base_url: str = "",
) -> str:
    """
    Garantit le bloc cf-demo-runtime avec token, demoUrl et apiBase non vides.
    Met à jour le script existant (corrige les démos avec apiBase manquant).
    """
    api = resolve_demo_api_base_url(api_base_url)
    clean_token = token.strip()
    if not clean_token or not api:
        return html

    title = (project_title or "Démo").strip() or "Démo"
    demo = demo_url.strip().rstrip("/")
    existing = _read_runtime_payload(html)
    payload = {
        "token": clean_token,
        "projectTitle": (existing or {}).get("projectTitle") or title,
        "demoUrl": demo or (existing or {}).get("demoUrl") or "",
        "apiBase": api,
    }

    script = _runtime_script_tag(payload)
    cleaned = _strip_runtime_script(html)
    return _insert_runtime_after_body_open(cleaned, script)


def inject_demo_runtime_config(
    html: str,
    *,
    token: str,
    project_title: str,
    demo_url: str,
    api_base_url: str,
) -> str:
    """
    Insère un bloc JSON lisible par premium_interaction_scripts (formulaire CapCore).
    """
    api = resolve_demo_api_base_url(api_base_url)
    payload = {
        "token": token.strip(),
        "projectTitle": (project_title or "Démo").strip() or "Démo",
        "demoUrl": demo_url.strip().rstrip("/"),
        "apiBase": api,
    }
    script = _runtime_script_tag(payload)
    cleaned = _strip_runtime_script(html)
    return _insert_runtime_after_body_open(cleaned, script)
