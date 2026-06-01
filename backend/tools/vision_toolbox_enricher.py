"""
VisionUI — enrichissement HTML via toolbox (photos, icônes SVG, illustrations unDraw).
"""

from __future__ import annotations

import logging
import re
from pydantic import BaseModel, Field
from html import escape
from typing import TYPE_CHECKING

from config import Settings, get_settings
from tools.replicate_image_gen import ReplicateImageGenerator
from tools.toolbox_media import (
    VISION_MIN_RELEVANT_PHOTOS,
    VISION_PHOTO_RELEVANCE_MIN,
    ToolboxIllustration,
    ToolboxPhoto,
    fetch_iconify_svg,
    relevant_photos,
    resolve_photo_query,
    search_toolbox_icons,
    search_toolbox_illustrations,
    search_toolbox_photos,
)
from tools.toolbox_sectors import get_sector_bundle, normalize_sector_key

if TYPE_CHECKING:
    from agents.architect_agent import ArchitectPlan

logger = logging.getLogger(__name__)

_IMG_SRC_RE = re.compile(
    r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'][^>]*>)',
    re.IGNORECASE,
)
_FEATURE_ICON_RE = re.compile(
    r'(<div\s+class=["\'][^"\']*cf-feature-icon[^"\']*["\']>\s*)([^<]{1,8})(\s*</div>)',
    re.IGNORECASE,
)
_ACTIVITY_ICON_RE = re.compile(
    r'(<div\s+class=["\'][^"\']*activity-icon[^"\']*["\']>\s*)([^<]{1,8})(\s*</div>)',
    re.IGNORECASE,
)
_EMPTY_STATE_RE = re.compile(
    r'(<p\s+class=["\'][^"\']*empty-state[^"\']*["\'][^>]*>)',
    re.IGNORECASE,
)
_404_HINT_RE = re.compile(r"\b404\b|page\s+introuvable|not\s+found", re.IGNORECASE)

_EMOJI_ICON_QUERIES: dict[str, str] = {
    "⚡": "zap",
    "🔒": "lock",
    "💬": "message",
    "✓": "check",
    "✔": "check",
    "€": "currency",
    "◎": "target",
    "+": "plus",
    "★": "star",
    "☆": "star",
    "📧": "mail",
    "📞": "phone",
}

_UNSPLASH_HOST = "images.unsplash.com"
_PLACEHOLDER_HOSTS = ("placeholder.com", "picsum.photos", "placehold.co")


class VisionEnrichStats(BaseModel):
    photos_stock: int = 0
    photos_replicate: int = 0
    icons_inlined: int = 0
    illustrations: int = 0
    photo_source: str = "none"
    tags: list[str] = Field(default_factory=list)


def _visual_query(plan: ArchitectPlan | None, prompt: str | None) -> tuple[str, str | None]:
    secteur = None
    query = ""
    if plan and plan.secteur:
        secteur = plan.secteur
    if plan:
        bundle = get_sector_bundle(plan.secteur or "")
        if bundle and bundle.mots_cles_visuels:
            query = bundle.mots_cles_visuels[0]
    if prompt:
        words = re.findall(r"[a-zA-ZÀ-ÿ]{4,}", prompt)
        if words:
            extra = " ".join(words[:4])
            query = f"{query} {extra}".strip() if query else extra
    if not query:
        query = resolve_photo_query("", secteur)
    return query[:120], secteur


def _is_replaceable_image_url(url: str) -> bool:
    low = url.lower()
    if _UNSPLASH_HOST in low:
        return True
    return any(host in low for host in _PLACEHOLDER_HOSTS)


def _absolute_asset_url(settings: Settings, asset: dict) -> str:
    local = asset.get("local_url") or f"/api/media/files/{asset['id']}"
    if local.startswith("http"):
        return local
    base = settings.backend_public_url.rstrip("/")
    return f"{base}{local}"


async def _persist_photo(
    photo: ToolboxPhoto,
    *,
    settings: Settings,
    project_id: str | None,
) -> str | None:
    from tools.media_library import try_save_generated_asset

    ext = "jpg" if photo.source == "unsplash" else "jpg"
    safe_id = re.sub(r"[^\w.\-]", "_", photo.id)[:48]
    asset = await try_save_generated_asset(
        url=photo.url_download or photo.url_full,
        filename=f"{photo.source}_{safe_id}.{ext}",
        project_id=project_id,
        source="generated",
        tags=[photo.source, "visionui"],
    )
    if not asset:
        return photo.url_full
    return _absolute_asset_url(settings, asset)


async def _persist_replicate_image(
    url: str,
    *,
    settings: Settings,
    project_id: str | None,
    index: int,
) -> str:
    from tools.media_library import try_save_generated_asset

    safe_pid = re.sub(r"[^\w.\-]", "_", (project_id or "vision"))[:32]
    asset = await try_save_generated_asset(
        url=url,
        filename=f"replicate_{safe_pid}_{index}.png",
        project_id=project_id,
        source="generated",
        tags=["replicate", "visionui"],
    )
    if asset:
        return _absolute_asset_url(settings, asset)
    return url


async def _persist_svg_resource(
    svg_markup: str,
    *,
    provider: str,
    resource_id: str,
    settings: Settings,
    project_id: str | None,
) -> str | None:
    from tools.media_library import try_save_svg_asset

    safe_id = re.sub(r"[^\w.\-]", "_", resource_id)[:48]
    asset = await try_save_svg_asset(
        svg_markup,
        filename=f"{provider}_{safe_id}.svg",
        project_id=project_id,
        tags=[provider, "visionui"],
    )
    if not asset:
        return None
    return _absolute_asset_url(settings, asset)


def _inline_svg_block(svg: str, *, size: int = 28) -> str:
    cleaned = svg.strip()
    if not cleaned.startswith("<svg"):
        return cleaned
    cleaned = re.sub(r'\s(width|height)=["\'][^"\']*["\']', "", cleaned, count=2)
    return (
        f'<span class="cf-iconify-inline" style="display:inline-flex;width:{size}px;'
        f'height:{size}px;vertical-align:middle" aria-hidden="true">'
        f'{cleaned}</span>'
    )


async def _resolve_photo_pool(
    query: str,
    secteur: str | None,
    *,
    settings: Settings,
    project_id: str | None,
    stats: VisionEnrichStats,
) -> list[str]:
    """Retourne des URLs absolues prêtes pour les balises <img>."""
    _, photos = await search_toolbox_photos(
        query, secteur=secteur, per_page=6, settings=settings
    )
    picked = relevant_photos(
        photos,
        min_count=VISION_MIN_RELEVANT_PHOTOS,
        min_score=VISION_PHOTO_RELEVANCE_MIN,
    )

    urls: list[str] = []
    if picked:
        stats.photo_source = "stock"
        for photo in picked:
            url = await _persist_photo(photo, settings=settings, project_id=project_id)
            if url:
                urls.append(url)
                stats.photos_stock += 1
                if photo.source not in stats.tags:
                    stats.tags.append(photo.source)
        return urls

    generator = ReplicateImageGenerator(settings)
    if not generator.is_configured():
        logger.info("VisionUI — stock photo insuffisant, Replicate non configuré")
        return urls

    stats.photo_source = "replicate"
    for index in range(3):
        prompt = f"{query}, professional web hero photo, high quality"
        if secteur:
            prompt = f"{prompt}, {normalize_sector_key(secteur)} industry"
        gen_url = await generator.generate_image(prompt, project_id=project_id)
        if not gen_url:
            break
        saved = await _persist_replicate_image(
            gen_url, settings=settings, project_id=project_id, index=index
        )
        urls.append(saved)
        stats.photos_replicate += 1
        if "replicate" not in stats.tags:
            stats.tags.append("replicate")
    return urls


async def _inject_icons(
    html: str,
    *,
    settings: Settings,
    project_id: str | None,
    stats: VisionEnrichStats,
) -> str:
    icon_cache: dict[str, str] = {}

    async def replace_emoji(match: re.Match[str], size: int) -> str:
        emoji = match.group(2).strip()
        query = _EMOJI_ICON_QUERIES.get(emoji)
        if not query:
            return match.group(0)
        if query not in icon_cache:
            _, icons = await search_toolbox_icons(query, limit=6, settings=settings)
            if not icons:
                return match.group(0)
            icon = icons[0]
            try:
                svg = await fetch_iconify_svg(icon.svg_url, settings)
            except Exception as exc:
                logger.debug("Iconify fetch %s: %s", icon.name, exc)
                return match.group(0)
            await _persist_svg_resource(
                svg,
                provider="iconify",
                resource_id=icon.name.replace(":", "_"),
                settings=settings,
                project_id=project_id,
            )
            icon_cache[query] = _inline_svg_block(svg, size=size)
            stats.icons_inlined += 1
            if "iconify" not in stats.tags:
                stats.tags.append("iconify")
        return f"{match.group(1)}{icon_cache[query]}{match.group(3)}"

    out = html
    for pattern, size in ((_FEATURE_ICON_RE, 28), (_ACTIVITY_ICON_RE, 22)):
        matches = list(pattern.finditer(out))
        if not matches:
            continue
        parts: list[str] = []
        last = 0
        for match in matches:
            parts.append(out[last : match.start()])
            parts.append(await replace_emoji(match, size))
            last = match.end()
        parts.append(out[last:])
        out = "".join(parts)
    return out


async def _inject_illustrations(
    html: str,
    *,
    settings: Settings,
    project_id: str | None,
    stats: VisionEnrichStats,
) -> str:
    queries: list[str] = []
    if _EMPTY_STATE_RE.search(html):
        queries.append("empty")
    if _404_HINT_RE.search(html):
        queries.append("404")

    if not queries:
        return html

    illustrations: list[ToolboxIllustration] = []
    for q in queries:
        _, batch = await search_toolbox_illustrations(q, limit=2, settings=settings)
        illustrations.extend(batch)

    if not illustrations:
        return html

    ill = illustrations[0]
    try:
        import httpx

        async with httpx.AsyncClient(
            timeout=settings.toolbox_http_timeout_seconds, follow_redirects=True
        ) as client:
            response = await client.get(ill.svg_url)
        response.raise_for_status()
        svg = response.text
    except Exception as exc:
        logger.debug("unDraw fetch %s: %s", ill.id, exc)
        return html

    await _persist_svg_resource(
        svg,
        provider="undraw",
        resource_id=ill.id,
        settings=settings,
        project_id=project_id,
    )
    stats.illustrations += 1
    if "undraw" not in stats.tags:
        stats.tags.append("undraw")

    block = (
        f'<div class="cf-undraw-illus" style="max-width:280px;margin:0 auto 1rem">'
        f'{svg}</div>'
    )

    def add_before_empty(match: re.Match[str]) -> str:
        return block + match.group(1)

    out = _EMPTY_STATE_RE.sub(add_before_empty, html, count=1)
    if queries and "404" in queries and _404_HINT_RE.search(out) and block not in out:
        out = out.replace("</body>", f"{block}</body>", 1)
    return out


def _inject_photos(html: str, photo_urls: list[str]) -> str:
    if not photo_urls:
        return html
    index = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal index
        src = match.group(2)
        if not _is_replaceable_image_url(src):
            return match.group(0)
        url = photo_urls[index % len(photo_urls)]
        index += 1
        return f"{match.group(1)}{escape(url, quote=True)}{match.group(3)}"

    return _IMG_SRC_RE.sub(replacer, html)


async def enrich_html_with_toolbox(
    html: str,
    *,
    plan: ArchitectPlan | None = None,
    prompt: str | None = None,
    settings: Settings | None = None,
    project_id: str | None = None,
) -> tuple[str, VisionEnrichStats]:
    """
    Enrichit le HTML avant capture VisionUI :
    photos stock (Pexels/Unsplash) ou Replicate, icônes Iconify inline, illustrations unDraw.
    """
    trimmed = html.strip()
    if not trimmed:
        return html, VisionEnrichStats()

    resolved = settings or get_settings()
    stats = VisionEnrichStats()
    query, secteur = _visual_query(plan, prompt)

    photo_urls = await _resolve_photo_pool(
        query, secteur, settings=resolved, project_id=project_id, stats=stats
    )
    out = _inject_photos(trimmed, photo_urls)
    out = await _inject_icons(out, settings=resolved, project_id=project_id, stats=stats)
    out = await _inject_illustrations(
        out, settings=resolved, project_id=project_id, stats=stats
    )
    if "product-card" in out and 'class="thumb"' in out:
        from tools.ecommerce_product_images import ensure_ecommerce_product_thumbnails

        template_id = "ecommerce_default"
        if plan and getattr(plan, "pricing_category", None) == "ecommerce":
            blob = f"{getattr(plan, 'secteur', '')} {prompt or ''}".lower()
            if any(x in blob for x in ("boulanger", "pâtiss", "patiss", "épicerie", "aliment")):
                template_id = "ecommerce_alimentaire"
            elif any(x in blob for x in ("mode", "fashion", "vêtement", "vetement")):
                template_id = "ecommerce_mode"
        out = ensure_ecommerce_product_thumbnails(out, template_id)
    return out, stats
