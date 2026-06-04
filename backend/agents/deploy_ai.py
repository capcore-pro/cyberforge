"""
DeployAI — injection images Pexels + déploiement Cloudflare Pages (cyberforge-demos).
"""

from __future__ import annotations

import logging
import re
from html import escape
from typing import Any

from config import get_settings
from tools.export_cloudflare import CloudflareExportError, deploy_html_demo
from tools.toolbox_media import search_toolbox_photos

logger = logging.getLogger(__name__)

_IMG_PEXELS_RE = re.compile(
    r"<img\b(?=[^>]*\bpexels-inject\b)([^>]*)/?>",
    re.IGNORECASE,
)
_ALT_RE = re.compile(r"""\balt=(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_SRC_RE = re.compile(r"""\bsrc=(["'])(.*?)\1""", re.IGNORECASE)


async def _pexels_url_for_alt(alt: str, *, sector: str | None) -> str | None:
    query = (alt or "").strip() or "business professional"
    settings = get_settings()
    _, photos = await search_toolbox_photos(
        query[:80],
        secteur=sector,
        per_page=3,
        settings=settings,
    )
    if not photos:
        return None
    photo = photos[0]
    return (photo.url_full or photo.url_download or "").strip() or None


def _set_img_src(attrs: str, url: str) -> str:
    safe_url = escape(url, quote=True)
    if _SRC_RE.search(attrs):
        return _SRC_RE.sub(f'src="{safe_url}"', attrs, count=1)
    return f'{attrs} src="{safe_url}"'


async def inject_pexels_images(html: str, *, sector: str | None = None) -> str:
    """Remplace les src des <img class=\"pexels-inject\"> par des URLs Pexels CDN."""
    index = 0

    async def _replace(match: re.Match[str]) -> str:
        nonlocal index
        attrs = match.group(1) or ""
        alt_m = _ALT_RE.search(attrs)
        alt = (alt_m.group(2) if alt_m else "").strip() or f"image {index + 1}"
        url = await _pexels_url_for_alt(alt, sector=sector)
        index += 1
        if not url:
            return match.group(0)
        attrs = _set_img_src(attrs, url)
        closing = "/" if match.group(0).rstrip().endswith("/>") else ""
        return f"<img{attrs}{closing}>"

    out = html
    for m in list(_IMG_PEXELS_RE.finditer(html)):
        replacement = await _replace(m)
        out = out.replace(m.group(0), replacement, 1)
    if index:
        logger.info("[DeployAI] %d image(s) Pexels injectée(s)", index)
    return out


class DeployAI:
    async def run(
        self,
        html: str,
        *,
        title: str = "",
        sector: str | None = None,
        project_type: str | None = None,
    ) -> dict[str, Any]:
        raw = (html or "").strip()
        if not raw:
            return {"url": "", "success": False, "error": "HTML vide"}

        enriched = await inject_pexels_images(raw, sector=sector)
        demo_title = (title or "CyberForge Demo").strip()[:120]

        try:
            production_url, demo_token, demo_password, unlock_url = await deploy_html_demo(
                html=enriched,
                title=demo_title,
                project_type=(project_type or "vitrine_next").strip(),
            )
            return {
                "url": production_url,
                "success": True,
                "demo_token": demo_token,
                "demo_password": demo_password,
                "unlock_url": unlock_url,
                "html": enriched,
            }
        except CloudflareExportError as exc:
            logger.error("[DeployAI] Cloudflare: %s", exc)
            return {
                "url": "",
                "success": False,
                "error": str(exc),
                "html": enriched,
            }
