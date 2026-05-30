"""
Recherche médias toolbox (Pexels, Unsplash, Iconify, unDraw) — usage API et agents.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings, plain_secret_str
from tools.toolbox_sectors import SECTEURS, normalize_sector_key

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
ICONIFY_SEARCH_URL = "https://api.iconify.design/search"
UNDRAW_ILLUSTRATIONS_URL = "https://undraw.co/api/illustrations"
UNDRAW_SEARCH_URL = "https://undraw.co/api/search"
PEXELS_UNSPLASH_THRESHOLD = 6

VISION_MIN_RELEVANT_PHOTOS = 3
VISION_PHOTO_RELEVANCE_MIN = 0.45


class ToolboxPhoto(BaseModel):
    id: str
    url_thumb: str
    url_full: str
    url_download: str
    source: str
    author: str | None = None
    author_url: str | None = None
    relevance_score: float = Field(
        default=0.0,
        description="Score heuristique 0–1 (ordre API + recoupement requête).",
    )


class ToolboxIcon(BaseModel):
    name: str
    svg_url: str
    prefix: str
    icon: str


class ToolboxIllustration(BaseModel):
    id: str
    title: str
    svg_url: str


def toolbox_http_timeout(settings: Settings | None = None) -> float:
    return (settings or get_settings()).toolbox_http_timeout_seconds


def resolve_photo_query(query: str, secteur: str | None) -> str:
    cleaned = query.strip()
    if cleaned:
        return cleaned[:120]
    if secteur:
        key = normalize_sector_key(secteur)
        sector = SECTEURS.get(key)
        if sector:
            keywords = sector.get("mots_cles_visuels") or []
            if keywords:
                return str(keywords[0])[:120]
    return "business"


def photo_relevance_score(query: str, *, rank: int, author: str | None = None) -> float:
    """
    Score de pertinence heuristique (les APIs stock ne renvoient pas de score explicite).
    L'ordre Pexels/Unsplash est préservé ; on pénalise le rang et on bonifie les tokens communs.
    """
    base = max(0.2, 0.95 - rank * 0.09)
    tokens = [t for t in re.split(r"[\s,;]+", query.lower()) if len(t) > 2]
    if not tokens:
        return base
    hay = " ".join((author or "").lower().split())
    if not hay:
        return base
    hits = sum(1 for t in tokens if t in hay)
    bonus = min(0.25, hits * 0.08)
    return min(1.0, base + bonus)


def relevant_photos(
    photos: list[ToolboxPhoto],
    *,
    min_count: int = VISION_MIN_RELEVANT_PHOTOS,
    min_score: float = VISION_PHOTO_RELEVANCE_MIN,
) -> list[ToolboxPhoto]:
    """Photos dont le score atteint le seuil ; vide si pas assez de résultats pertinents."""
    picked = [p for p in photos if p.relevance_score >= min_score]
    if len(picked) < min_count:
        return []
    return picked[: max(min_count, len(picked))]


async def search_toolbox_photos(
    query: str,
    *,
    secteur: str | None = None,
    per_page: int = 6,
    settings: Settings | None = None,
) -> tuple[str, list[ToolboxPhoto]]:
    resolved = settings or get_settings()
    effective_query = resolve_photo_query(query, secteur)
    if not resolved.pexels_configured and not resolved.unsplash_configured:
        return effective_query, []

    photos: list[ToolboxPhoto] = []
    timeout = toolbox_http_timeout(resolved)
    async with httpx.AsyncClient(timeout=timeout) as client:
        photos = await _fetch_pexels_photos(client, effective_query, per_page, resolved)
        if len(photos) < PEXELS_UNSPLASH_THRESHOLD and resolved.unsplash_configured:
            remaining = per_page - len(photos)
            if remaining > 0:
                extra = await _fetch_unsplash_photos(
                    client, effective_query, remaining, resolved
                )
                seen = {p.url_full for p in photos}
                for item in extra:
                    if item.url_full not in seen:
                        photos.append(item)
                        seen.add(item.url_full)
                    if len(photos) >= per_page:
                        break

    scored: list[ToolboxPhoto] = []
    for rank, photo in enumerate(photos[:per_page]):
        score = photo_relevance_score(
            effective_query, rank=rank, author=photo.author
        )
        scored.append(photo.model_copy(update={"relevance_score": score}))
    return effective_query, scored


async def search_toolbox_icons(
    query: str,
    *,
    limit: int = 24,
    settings: Settings | None = None,
) -> tuple[str, list[ToolboxIcon]]:
    effective_query = query.strip() or "star"
    resolved = settings or get_settings()
    timeout = toolbox_http_timeout(resolved)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            ICONIFY_SEARCH_URL,
            params={"query": effective_query, "limit": limit},
        )
    if response.status_code >= 400:
        logger.warning("Iconify search HTTP %s", response.status_code)
        return effective_query, []

    payload = response.json()
    icon_ids = payload.get("icons") or []
    icones: list[ToolboxIcon] = []
    for full_name in icon_ids[:limit]:
        name = str(full_name).strip()
        if not name or ":" not in name:
            continue
        prefix, icon = name.split(":", 1)
        icones.append(
            ToolboxIcon(
                name=name,
                svg_url=f"https://api.iconify.design/{prefix}/{icon}.svg",
                prefix=prefix,
                icon=icon,
            )
        )
    return effective_query, icones


async def search_toolbox_illustrations(
    query: str,
    *,
    limit: int = 12,
    settings: Settings | None = None,
) -> tuple[str, list[ToolboxIllustration]]:
    effective_query = query.strip() or "business"
    resolved = settings or get_settings()
    timeout = toolbox_http_timeout(resolved)
    async with httpx.AsyncClient(timeout=timeout) as client:
        illustrations = await _fetch_undraw_illustrations(
            client, effective_query, limit
        )
    return effective_query, illustrations


async def fetch_iconify_svg(svg_url: str, settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    timeout = toolbox_http_timeout(resolved)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(svg_url)
    response.raise_for_status()
    return response.text


async def _fetch_pexels_photos(
    client: httpx.AsyncClient,
    query: str,
    per_page: int,
    settings: Settings,
) -> list[ToolboxPhoto]:
    api_key = plain_secret_str(settings.pexels_api_key)
    if not api_key:
        return []

    response = await client.get(
        PEXELS_SEARCH_URL,
        params={"query": query, "per_page": per_page, "page": 1},
        headers={"Authorization": api_key},
    )
    if response.status_code >= 400:
        logger.warning("Pexels search HTTP %s", response.status_code)
        return []

    payload = response.json()
    items: list[ToolboxPhoto] = []
    for photo in payload.get("photos") or []:
        pid = photo.get("id")
        src = photo.get("src") or {}
        thumb = src.get("tiny") or src.get("small") or ""
        full = src.get("large") or src.get("large2x") or src.get("original") or ""
        download = src.get("original") or full
        if pid is None or not thumb or not full:
            continue
        items.append(
            ToolboxPhoto(
                id=f"pexels-{pid}",
                url_thumb=str(thumb),
                url_full=str(full),
                url_download=str(download),
                source="pexels",
                author=(photo.get("photographer") or "").strip() or None,
                author_url=(photo.get("photographer_url") or "").strip() or None,
            )
        )
    return items


async def _fetch_unsplash_photos(
    client: httpx.AsyncClient,
    query: str,
    per_page: int,
    settings: Settings,
) -> list[ToolboxPhoto]:
    access_key = plain_secret_str(settings.unsplash_access_key)
    if not access_key or per_page < 1:
        return []

    response = await client.get(
        UNSPLASH_SEARCH_URL,
        params={"query": query, "per_page": per_page, "page": 1},
        headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
    )
    if response.status_code >= 400:
        logger.warning("Unsplash search HTTP %s", response.status_code)
        return []

    payload = response.json()
    items: list[ToolboxPhoto] = []
    for photo in payload.get("results") or []:
        pid = str(photo.get("id") or "")
        urls = photo.get("urls") or {}
        links = photo.get("links") or {}
        thumb = urls.get("thumb") or urls.get("small") or ""
        full = urls.get("regular") or urls.get("full") or ""
        download = links.get("download") or urls.get("full") or full
        user = photo.get("user") or {}
        user_links = user.get("links") or {}
        if not pid or not thumb or not full:
            continue
        items.append(
            ToolboxPhoto(
                id=f"unsplash-{pid}",
                url_thumb=str(thumb),
                url_full=str(full),
                url_download=str(download),
                source="unsplash",
                author=(user.get("name") or "").strip() or None,
                author_url=(user_links.get("html") or "").strip() or None,
            )
        )
    return items


async def _fetch_undraw_illustrations(
    client: httpx.AsyncClient,
    query: str,
    limit: int,
) -> list[ToolboxIllustration]:
    params = {"q": query, "limit": limit}
    response = await client.get(UNDRAW_ILLUSTRATIONS_URL, params=params)
    if response.status_code >= 400:
        response = await client.get(UNDRAW_SEARCH_URL, params=params)
    if response.status_code >= 400:
        logger.warning("unDraw HTTP %s", response.status_code)
        return []

    payload = response.json()
    raw_items: list[dict[str, Any]] = []
    if isinstance(payload.get("results"), list):
        raw_items = payload["results"]
    elif isinstance(payload.get("illustrations"), list):
        raw_items = payload["illustrations"]
    elif isinstance(payload.get("illos"), list):
        raw_items = payload["illos"]

    items: list[ToolboxIllustration] = []
    for row in raw_items[:limit]:
        if not isinstance(row, dict):
            continue
        ill_id = str(
            row.get("_id") or row.get("id") or row.get("newSlug") or row.get("slug") or ""
        )
        title = str(row.get("title") or row.get("name") or "Illustration").strip()
        svg_url = str(
            row.get("media")
            or row.get("image")
            or row.get("svg_url")
            or row.get("url")
            or "",
        ).strip()
        if not ill_id or not svg_url:
            continue
        items.append(
            ToolboxIllustration(id=ill_id, title=title, svg_url=svg_url)
        )
    return items
