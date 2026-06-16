"""
Export ZIP d'un site HTML — extraction CSS/JS inline et README déploiement.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from datetime import UTC, datetime

_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_SCRIPT_INLINE_RE = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def slugify_project_title(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name or "")
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_name.lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", lowered)
    dashed = re.sub(r"\s+", "-", cleaned.strip())
    collapsed = re.sub(r"-+", "-", dashed)
    return collapsed[:50].strip("-") or "projet"


def zip_filename_for_project(project_title: str, *, on_date: datetime | None = None) -> str:
    when = on_date or datetime.now(UTC)
    return f"{slugify_project_title(project_title)}-{when.strftime('%Y-%m-%d')}.zip"


def extract_inline_styles(html: str) -> tuple[str, str]:
    """Retire les <style> inline et retourne (html, css concaténé)."""
    chunks: list[str] = []

    def repl(match: re.Match[str]) -> str:
        css = (match.group(1) or "").strip()
        if css:
            chunks.append(css)
        return ""

    cleaned = _STYLE_RE.sub(repl, html)
    return cleaned, "\n\n".join(chunks).strip()


def extract_inline_scripts(html: str) -> tuple[str, str]:
    """Retire les <script> inline (sans src) et retourne (html, js concaténé)."""
    chunks: list[str] = []

    def repl(match: re.Match[str]) -> str:
        js = (match.group(1) or "").strip()
        if js:
            chunks.append(js)
        return ""

    cleaned = _SCRIPT_INLINE_RE.sub(repl, html)
    return cleaned, "\n\n".join(chunks).strip()


def _inject_asset_tags(html: str, *, css: bool, js: bool) -> str:
    tags: list[str] = []
    if css:
        tags.append('<link rel="stylesheet" href="assets/style.css">')
    if js:
        tags.append('<script src="assets/script.js"></script>')
    if not tags:
        return html
    block = "\n".join(tags)
    if re.search(r"</head>", html, re.IGNORECASE):
        return re.sub(r"</head>", f"{block}\n</head>", html, count=1, flags=re.IGNORECASE)
    return f"{block}\n{html}"


def build_readme(project_title: str, *, on_date: datetime | None = None) -> str:
    when = on_date or datetime.now(UTC)
    date_label = when.strftime("%Y-%m-%d %H:%M UTC")
    title = (project_title or "Projet").strip() or "Projet"
    return f"""Site généré par CyberForge
Date : {date_label}
Projet : {title}

DÉPLOIEMENT :
Option 1 — Cloudflare Pages :
  Glissez ce dossier sur pages.cloudflare.com

Option 2 — Hébergement FTP :
  Uploadez tous les fichiers dans votre répertoire web

Option 3 — Ouvrir localement :
  Ouvrez index.html dans votre navigateur
"""


def prepare_site_export_files(
    html: str,
    project_title: str,
    *,
    on_date: datetime | None = None,
    remove_watermark: bool = True,
) -> dict[str, str]:
    """Prépare index.html + assets pour l'archive ZIP."""
    when = on_date or datetime.now(UTC)
    raw_html = (html or "").strip()
    if not raw_html:
        raise ValueError("HTML vide")

    if remove_watermark:
        from tools.watermark import remove_watermark as strip_watermark

        raw_html = strip_watermark(raw_html)

    without_styles, css = extract_inline_styles(raw_html)
    without_scripts, js = extract_inline_scripts(without_styles)
    index_html = _inject_asset_tags(
        without_scripts,
        css=bool(css),
        js=bool(js),
    )

    files: dict[str, str] = {
        "index.html": index_html,
        "assets/style.css": css or "/* Aucun CSS inline extrait */",
        "assets/script.js": js or "// Aucun JavaScript inline extrait",
        "assets/README.txt": build_readme(project_title, on_date=when),
    }
    return files


def build_site_export_zip(
    html: str,
    project_title: str,
    *,
    on_date: datetime | None = None,
    remove_watermark: bool = True,
) -> tuple[bytes, str]:
    """Construit l'archive ZIP en mémoire."""
    files = prepare_site_export_files(
        html,
        project_title,
        on_date=on_date,
        remove_watermark=remove_watermark,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.writestr(path, files[path].encode("utf-8"))
    filename = zip_filename_for_project(project_title, on_date=on_date)
    return buf.getvalue(), filename
