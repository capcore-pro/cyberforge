"""
Normalisation HTML vitrine — document complet vanilla (Playwright / BugHunter).
"""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

_LAST_VITRINE_DUMP = Path(__file__).resolve().parent.parent / "temp" / "_last_vitrine_preview.html"

_REACT_MARKERS = re.compile(
    r"\b(import\s+.*from\s+['\"]react|export\s+default|createRoot\s*\(|"
    r"useState\s*\(|useEffect\s*\(|className\s*=)",
    re.IGNORECASE,
)

_EXTERNAL_FRAMEWORK_RE = re.compile(
    r"<script[^>]+src=[\"'][^\"']*(?:react|vue|angular|next)[^\"']*[\"']",
    re.IGNORECASE,
)


def dump_last_vitrine_html(html: str) -> None:
    """Persiste le dernier HTML vitrine post-traité pour inspection."""
    try:
        _LAST_VITRINE_DUMP.parent.mkdir(parents=True, exist_ok=True)
        _LAST_VITRINE_DUMP.write_text(html, encoding="utf-8")
    except OSError:
        pass


def extract_unlocked_demo_html(html: str) -> str:
    """
    Prépare le HTML pour Playwright : déverrouille la démo CapCore ou extrait le corps.
    """
    low = html.lower()
    if "cf-login-screen" not in low and "cf-demo-content" not in low:
        return html

    unlock_css = (
        "<style id=\"cf-playwright-unlock\">"
        "#cf-login-screen{display:none!important;visibility:hidden!important}"
        "#cf-demo-content{display:block!important;visibility:visible!important}"
        "#cf-demo-content.cf-unlocked{display:block!important}"
        "</style>"
    )
    if unlock_css not in html:
        if re.search(r"</head>", html, re.I):
            html = re.sub(r"(</head>)", unlock_css + r"\1", html, count=1, flags=re.I)
        elif re.search(r"<body[^>]*>", html, re.I):
            html = re.sub(
                r"(<body[^>]*>)",
                r"\1" + unlock_css,
                html,
                count=1,
                flags=re.I,
            )
        else:
            html = unlock_css + html

    start_m = re.search(r'<div[^>]+id=["\']cf-demo-content["\'][^>]*>', html, re.I)
    if not start_m:
        return html
    inner_start = start_m.end()
    body_end = re.search(r"</body>", html[inner_start:], re.I)
    if not body_end:
        return html
    inner = html[inner_start : inner_start + body_end.start()].strip()
    if len(inner) > 400 and "```" not in inner[:200]:
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        title = (title_m.group(1) if title_m else "Site vitrine").strip()
        return normalize_vitrine_html_document(inner, page_title=title, client_name="")
    return html


def strip_react_and_framework_refs(html: str) -> str:
    """Retire scripts externes React/Vue et blocs JSX visibles."""
    out = _EXTERNAL_FRAMEWORK_RE.sub("", html)
    if _REACT_MARKERS.search(_strip_tags_for_scan(out)):
        # Remplacer par squelette minimal plutôt que livrer du React cassé
        return ""
    return out


def _strip_tags_for_scan(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    return text


def normalize_vitrine_html_document(
    html: str,
    *,
    page_title: str = "Site vitrine",
    client_name: str = "",
) -> str:
    """
    Garantit <!DOCTYPE html>, <html>, <head> (charset + title), <body> avec hero h1 + contact.
    Vanilla uniquement — pas de React/Vue.
    """
    raw = (html or "").strip()
    if not raw:
        raw = ""

    cleaned = strip_react_and_framework_refs(raw)
    if not cleaned and raw:
        cleaned = raw  # conserver si pas de React détecté dans le corps visible

    title = html_lib.escape((page_title or client_name or "Site vitrine").strip())
    name = html_lib.escape((client_name or page_title or "Notre entreprise").strip())

    # Extraire body/head si document partiel
    body_inner = cleaned
    head_extra = ""
    if re.search(r"<html", cleaned, re.I):
        head_m = re.search(r"<head[^>]*>([\s\S]*?)</head>", cleaned, re.I)
        if head_m:
            head_extra = head_m.group(1)
            tm = re.search(r"<title[^>]*>([^<]*)</title>", head_extra, re.I)
            if tm and tm.group(1).strip():
                title = html_lib.escape(tm.group(1).strip())
        body_m = re.search(r"<body[^>]*>([\s\S]*?)</body>", cleaned, re.I)
        if body_m:
            body_inner = body_m.group(1)

    if not re.search(r"charset\s*=", head_extra, re.I):
        head_extra = '<meta charset="UTF-8" />\n' + head_extra
    if not re.search(r"<title", head_extra, re.I):
        head_extra = f"<title>{title}</title>\n" + head_extra

    if not re.search(r"<h1\b", body_inner, re.I):
        body_inner = (
            f'<section id="hero" class="cf-vitrine-hero">'
            f"<h1>{name}</h1>"
            f"<p>Bienvenue — découvrez nos services.</p>"
            f"</section>\n"
            + body_inner
        )

    low = body_inner.lower()
    if 'id="contact"' not in low and "cf-contact-form" not in low:
        body_inner += f"""
<section id="contact" class="cf-vitrine-contact">
  <h2>Contact</h2>
  <p>Contactez {name}.</p>
  <form id="cf-contact-form" action="#" method="post" onsubmit="return false;">
    <label>Nom <input type="text" name="name" required /></label>
    <label>Email <input type="email" name="email" required /></label>
    <label>Message <textarea name="message" required></textarea></label>
    <button type="submit">Envoyer</button>
  </form>
</section>
"""

    if not re.search(r"<style", head_extra, re.I) and not re.search(
        r"style\s*=", body_inner, re.I
    ):
        head_extra += """
<style>
  body { font-family: system-ui, sans-serif; margin: 0; line-height: 1.5; color: #1e293b; }
  #hero { padding: 3rem 1.5rem; background: #f8fafc; }
  #contact { padding: 3rem 1.5rem; max-width: 40rem; margin: 0 auto; }
  #cf-contact-form label { display: block; margin-bottom: 0.75rem; }
  #cf-contact-form input, #cf-contact-form textarea { width: 100%; padding: 0.5rem; }
</style>
"""

    doc = f"""<!DOCTYPE html>
<html lang="fr">
<head>
{head_extra.strip()}
</head>
<body>
{body_inner.strip()}
</body>
</html>
"""
    from tools.vitrine_shell import apply_vitrine_premium_shell
    from tools.client_content_profile import (
        ClientContentProfile,
        build_client_content_profile,
    )

    profile = build_client_content_profile(
        user_prompt="",
    )
    if client_name:
        profile = ClientContentProfile(
            company_name=client_name,
            sector=profile.sector,
            city=profile.city,
            keywords=profile.keywords,
        )
    doc = apply_vitrine_premium_shell(doc, profile)
    dump_last_vitrine_html(doc)
    return doc
