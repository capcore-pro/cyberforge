"""
MediaAI — upscaling Replicate, génération image et recherche Pexels.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx

from config import Settings, get_settings, plain_secret_str
from cost_tracker import maybe_track_cost
from tools.replicate_image_gen import ReplicateImageGenerator
from tools.replicate_screenshot import (
    REPLICATE_API_BASE,
    ReplicateScreenshotError,
    _auth_header,
    _extract_output_url,
)
from tools.toolbox_media import ToolboxPhoto, search_toolbox_photos

logger = logging.getLogger(__name__)

UPSCALE_MODEL = "nightmareai/real-esrgan"

_STYLE_SUFFIXES: dict[str, str] = {
    "premium": ", professional photography, high quality, 4k, sharp",
    "product": ", product photo, white background, studio lighting",
    "hero": ", wide angle, cinematic, high resolution landscape",
}


def _replicate_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(plain_secret_str(s.replicate_api_key))


def _pexels_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(s.pexels_configured)


def _apply_style_prompt(prompt: str, style: str) -> str:
    base = prompt.strip()
    suffix = _STYLE_SUFFIXES.get(style.strip().lower(), _STYLE_SUFFIXES["premium"])
    return f"{base}{suffix}"[:500]


async def _run_replicate_model(
    model_slug: str,
    input_payload: dict[str, Any],
    *,
    project_id: str | None = None,
    settings: Settings | None = None,
) -> str | None:
    resolved = settings or get_settings()
    api_key = plain_secret_str(resolved.replicate_api_key)
    if not api_key:
        return None

    parts = model_slug.strip().split("/", 1)
    if len(parts) != 2:
        logger.warning("[MediaAI] modèle Replicate invalide : %s", model_slug)
        return None
    owner, name = parts
    create_url = f"{REPLICATE_API_BASE}/models/{owner}/{name}/predictions"
    timeout_seconds = max(90.0, float(resolved.vision_replicate_timeout_seconds))
    timeout = httpx.Timeout(timeout_seconds)
    headers = {
        **_auth_header(api_key),
        "Content-Type": "application/json",
        "Prefer": f"wait={int(min(60, timeout_seconds))}",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                create_url,
                json={"input": input_payload},
                headers=headers,
            )
            if response.status_code >= 400:
                raise ReplicateScreenshotError(
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )
            payload = response.json()
            status = payload.get("status")
            if status == "succeeded":
                url = _extract_output_url(payload.get("output"))
                if url:
                    maybe_track_cost(project_id, "replicate", {"images": 1})
                    return url
                raise ReplicateScreenshotError("Sortie Replicate vide.")

            if status in ("failed", "canceled"):
                raise ReplicateScreenshotError(
                    str(payload.get("error") or f"Statut {status}")
                )

            prediction_id = payload.get("id")
            if not prediction_id:
                raise ReplicateScreenshotError("Réponse sans id de prédiction.")
            return await _poll_prediction(
                client,
                str(prediction_id),
                api_key=api_key,
                project_id=project_id,
                settings=resolved,
            )
    except (ReplicateScreenshotError, httpx.HTTPError) as exc:
        logger.warning("[MediaAI] Replicate %s — %s", model_slug, exc)
        return None


async def _poll_prediction(
    client: httpx.AsyncClient,
    prediction_id: str,
    *,
    api_key: str,
    project_id: str | None,
    settings: Settings,
) -> str | None:
    poll_url = f"{REPLICATE_API_BASE}/predictions/{prediction_id}"
    headers = _auth_header(api_key)
    deadline = max(90.0, float(settings.vision_replicate_timeout_seconds))
    interval = max(0.5, settings.vision_replicate_poll_seconds)
    elapsed = 0.0

    while elapsed < deadline:
        response = await client.get(poll_url, headers=headers)
        if response.status_code >= 400:
            raise ReplicateScreenshotError(f"Poll HTTP {response.status_code}")
        payload = response.json()
        status = payload.get("status")
        if status == "succeeded":
            url = _extract_output_url(payload.get("output"))
            if url:
                maybe_track_cost(project_id, "replicate", {"images": 1})
                return url
            raise ReplicateScreenshotError("Sortie Replicate vide.")
        if status in ("failed", "canceled"):
            raise ReplicateScreenshotError(
                str(payload.get("error") or f"Statut {status}")
            )
        await asyncio.sleep(interval)
        elapsed += interval

    raise ReplicateScreenshotError("Délai Replicate dépassé.")


async def upscale_image(
    image_url: str,
    scale: Literal[2, 4] = 4,
    *,
    project_id: str | None = None,
) -> dict[str, Any] | None:
    """Upscale via nightmareai/real-esrgan."""
    if not _replicate_configured():
        return None
    url = (image_url or "").strip()
    if not url.startswith("http"):
        logger.warning("[MediaAI] upscale_image — URL invalide")
        return None
    safe_scale = 4 if int(scale) >= 4 else 2
    out_url = await _run_replicate_model(
        UPSCALE_MODEL,
        {"image": url, "scale": safe_scale},
        project_id=project_id,
    )
    if not out_url:
        return None
    return {"url": out_url, "scale": safe_scale}


async def generate_image(
    prompt: str,
    style: str = "premium",
    *,
    project_id: str | None = None,
) -> dict[str, Any] | None:
    """Génère une image (wrapper replicate_image_gen + suffixe style)."""
    if not _replicate_configured():
        return None
    full_prompt = _apply_style_prompt(prompt, style)
    generator = ReplicateImageGenerator()
    url = await generator.generate_image(full_prompt, project_id=project_id)
    if not url:
        return None
    return {"url": url, "prompt_used": full_prompt}


def _photo_to_result(photo: ToolboxPhoto) -> dict[str, str]:
    return {
        "url": photo.url_full,
        "thumbnail": photo.url_thumb,
        "author": photo.author or "",
        "source": "pexels" if photo.source == "pexels" else photo.source,
    }


async def search_pexels(
    query: str,
    count: int = 12,
    *,
    settings: Settings | None = None,
) -> list[dict[str, str]]:
    """Recherche photos Pexels (via toolbox_media)."""
    if not _pexels_configured(settings):
        return []
    cleaned = (query or "").strip()
    if not cleaned:
        return []
    limit = max(1, min(int(count), 30))
    _effective, photos = await search_toolbox_photos(
        cleaned,
        per_page=limit,
        settings=settings,
    )
    return [
        _photo_to_result(p)
        for p in photos
        if p.source == "pexels" and p.url_full
    ]


class MediaAIAgent:
    """Wrapper pipeline / API médiathèque."""

    async def upscale(
        self,
        image_url: str,
        scale: int = 4,
        *,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        safe_scale: Literal[2, 4] = 4 if int(scale) >= 4 else 2
        return await upscale_image(
            image_url,
            safe_scale,
            project_id=project_id,
        )

    async def generate(
        self,
        prompt: str,
        style: str = "premium",
        *,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        return await generate_image(prompt, style=style, project_id=project_id)

    async def search(self, query: str, count: int = 12) -> list[dict[str, str]]:
        return await search_pexels(query, count)
