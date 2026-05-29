"""Résolution d'images via l'API Unsplash Search (Phase 4.2c)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from config import Settings, get_settings, plain_secret_str
from cost_tracker import maybe_track_cost
from tools.vitrine.content_schema import UnsplashImage, VitrineSiteContent

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
DEFAULT_WIDTH = 1200
DEFAULT_QUALITY = 80

Orientation = Literal["landscape", "portrait", "squarish"]


class UnsplashResolverError(Exception):
    """Erreur lors de la résolution d'images Unsplash."""


@dataclass(frozen=True)
class UnsplashResolveStats:
    resolved: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class _ImageSlot:
    path: tuple[str, ...]
    query: str | None
    orientation: Orientation | None
    pick_index: int


class UnsplashImageResolver:
    """Remplace les URLs d'images par des photos Unsplash API (attribution incluse)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._access_key = plain_secret_str(self._settings.unsplash_access_key)
        self._timeout = self._settings.unsplash_http_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self._access_key)

    async def resolve_content(
        self,
        content: VitrineSiteContent,
        *,
        locale: str = "fr",
        project_id: str | None = None,
    ) -> tuple[VitrineSiteContent, UnsplashResolveStats]:
        if not self.configured:
            logger.info("UnsplashResolver — UNSPLASH_ACCESS_KEY absente, images inchangées")
            return content, UnsplashResolveStats(resolved=0, skipped=0, failed=0)

        slots = _image_slots(content)
        if not slots:
            return content, UnsplashResolveStats(resolved=0, skipped=0, failed=0)

        data = content.model_dump()
        cache: dict[str, dict[str, Any]] = {}
        resolved = skipped = failed = 0

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for slot in slots:
                image_dict = _get_nested(data, slot.path)
                if not isinstance(image_dict, dict):
                    skipped += 1
                    continue

                search_query = (
                    slot.query
                    or image_dict.get("imageQuery")
                    or image_dict.get("alt")
                    or ""
                ).strip()
                if not search_query:
                    skipped += 1
                    continue

                cache_key = f"{search_query.lower()}|{slot.orientation or ''}"
                if cache_key in cache:
                    _set_nested(data, slot.path, cache[cache_key])
                    resolved += 1
                    continue

                try:
                    image = await self._search_photo(
                        client,
                        search_query,
                        orientation=slot.orientation,
                        pick_index=slot.pick_index,
                        alt_fallback=str(image_dict.get("alt") or search_query),
                        locale=locale,
                        project_id=project_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "UnsplashResolver — échec query=%r : %s",
                        search_query[:60],
                        exc,
                    )
                    failed += 1
                    continue

                if image is None:
                    skipped += 1
                    continue

                payload = image.model_dump(by_alias=True)
                cache[cache_key] = payload
                _set_nested(data, slot.path, payload)
                resolved += 1

        return VitrineSiteContent.model_validate(data), UnsplashResolveStats(
            resolved=resolved,
            skipped=skipped,
            failed=failed,
        )

    async def _search_photo(
        self,
        client: httpx.AsyncClient,
        query: str,
        *,
        orientation: Orientation | None,
        pick_index: int,
        alt_fallback: str,
        locale: str,
        project_id: str | None = None,
    ) -> UnsplashImage | None:
        params: dict[str, str | int] = {
            "query": query[:120],
            "per_page": 5,
            "page": 1 + (pick_index // 5),
        }
        lang = (locale or "fr")[:2]
        if lang:
            params["lang"] = lang
        if orientation:
            params["orientation"] = orientation

        response = await client.get(
            UNSPLASH_SEARCH_URL,
            params=params,
            headers={
                "Authorization": f"Client-ID {self._access_key}",
                "Accept-Version": "v1",
            },
        )
        response.raise_for_status()
        maybe_track_cost(project_id, "unsplash", {"requests": 1})
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            return None

        photo = results[pick_index % len(results)]
        urls = photo.get("urls") or {}
        raw_url = urls.get("regular") or urls.get("small") or ""
        if not raw_url:
            return None

        user = photo.get("user") or {}
        photographer = (user.get("name") or "").strip() or None
        links = user.get("links") or {}
        photographer_url = (links.get("html") or "").strip() or None
        alt = (
            photo.get("alt_description") or photo.get("description") or alt_fallback or query
        )
        alt_text = str(alt).strip()[:200]
        photo_url = _sized_unsplash_url(raw_url, width=DEFAULT_WIDTH)
        photo_id = str(photo.get("id") or "").strip()

        await self._persist_unsplash_image(
            photo_url=photo_url,
            photo_id=photo_id,
            project_id=project_id,
            query_keyword=query[:120],
        )

        return UnsplashImage(
            url=photo_url,
            alt=alt_text or query[:200],
            photographer=photographer,
            photographerUrl=photographer_url,
            imageQuery=query[:120],
        )

    async def _persist_unsplash_image(
        self,
        *,
        photo_url: str,
        photo_id: str,
        project_id: str | None,
        query_keyword: str,
    ) -> None:
        from tools.media_library import try_save_generated_asset

        safe_id = photo_id or "unknown"
        keyword = (query_keyword or "search").strip()[:60] or "search"
        await try_save_generated_asset(
            url=photo_url,
            filename=f"unsplash_{safe_id}.jpg",
            project_id=project_id,
            source="generated",
            tags=["unsplash", keyword],
        )


def _sized_unsplash_url(url: str, *, width: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["auto"] = ["format"]
    query["fit"] = ["crop"]
    query["w"] = [str(width)]
    query["q"] = [str(DEFAULT_QUALITY)]
    flat = {k: v[-1] if v else "" for k, v in query.items()}
    return urlunparse(parsed._replace(query=urlencode(flat)))


def _image_slots(content: VitrineSiteContent) -> list[_ImageSlot]:
    slots: list[_ImageSlot] = [
        _ImageSlot(
            path=("home", "hero", "image"),
            query=content.home.hero.image.imageQuery,
            orientation="landscape",
            pick_index=0,
        ),
    ]
    for idx, card in enumerate(content.home.servicesPreview):
        slots.append(
            _ImageSlot(
                path=("home", "servicesPreview", str(idx), "image"),
                query=card.image.imageQuery or card.title,
                orientation="squarish",
                pick_index=idx + 1,
            ),
        )
    for idx, section in enumerate(content.servicesPage.sections):
        slots.append(
            _ImageSlot(
                path=("servicesPage", "sections", str(idx), "image"),
                query=section.image.imageQuery or section.title,
                orientation="landscape",
                pick_index=idx + 4,
            ),
        )
    return slots


def _get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = data
    for key in path:
        if isinstance(node, list):
            node = node[int(key)]
        elif isinstance(node, dict):
            node = node.get(key)
        else:
            return None
    return node


def _set_nested(data: dict[str, Any], path: tuple[str, ...], value: dict[str, Any]) -> None:
    node: Any = data
    keys = list(path)
    for key in keys[:-1]:
        node = node[int(key)] if isinstance(node, list) else node[key]
    last = keys[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


async def resolve_vitrine_images(
    content: VitrineSiteContent,
    *,
    settings: Settings | None = None,
    locale: str | None = None,
    project_id: str | None = None,
) -> tuple[VitrineSiteContent, UnsplashResolveStats]:
    resolver = UnsplashImageResolver(settings)
    loc = locale or content.meta.locale or "fr"
    return await resolver.resolve_content(content, locale=loc, project_id=project_id)
