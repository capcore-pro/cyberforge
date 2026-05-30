"""
Génération d'images via Replicate (fallback VisionUI lorsque le stock photo est insuffisant).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str
from cost_tracker import maybe_track_cost
from tools.replicate_screenshot import (
    REPLICATE_API_BASE,
    ReplicateScreenshotError,
    _auth_header,
    _extract_output_url,
)

logger = logging.getLogger(__name__)

DEFAULT_REPLICATE_IMAGE_MODEL = "black-forest-labs/flux-schnell"


class ReplicateImageGenerator:
    """Text-to-image Replicate pour compléter les visuels manquants."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def api_key(self) -> str:
        return plain_secret_str(self._settings.replicate_api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def model_slug(self) -> str:
        raw = self._settings.replicate_image_model
        slug = plain_secret_str(raw) if raw else ""
        return slug or DEFAULT_REPLICATE_IMAGE_MODEL

    async def generate_image(
        self,
        prompt: str,
        *,
        project_id: str | None = None,
    ) -> str | None:
        if not self.is_configured():
            return None
        cleaned = prompt.strip()
        if not cleaned:
            return None

        input_payload: dict[str, Any] = {"prompt": cleaned[:500]}
        try:
            return await self._run_prediction(input_payload, project_id=project_id)
        except (ReplicateScreenshotError, httpx.HTTPError) as exc:
            logger.warning("Replicate image gen — %s", exc)
            return None

    async def _run_prediction(
        self,
        input_payload: dict[str, Any],
        *,
        project_id: str | None,
    ) -> str:
        owner, name = self._split_model_slug(self.model_slug)
        create_url = f"{REPLICATE_API_BASE}/models/{owner}/{name}/predictions"
        timeout_seconds = max(
            90.0, float(self._settings.vision_replicate_timeout_seconds)
        )
        timeout = httpx.Timeout(timeout_seconds)
        headers = {
            **_auth_header(self.api_key),
            "Content-Type": "application/json",
            "Prefer": f"wait={int(min(60, timeout_seconds))}",
        }

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
                raise ReplicateScreenshotError("Sortie image vide.")

            if status in ("failed", "canceled"):
                raise ReplicateScreenshotError(
                    str(payload.get("error") or f"Statut {status}")
                )

            prediction_id = payload.get("id")
            if not prediction_id:
                raise ReplicateScreenshotError("Réponse sans id de prédiction.")
            return await self._poll(client, str(prediction_id), project_id=project_id)

    async def _poll(
        self,
        client: httpx.AsyncClient,
        prediction_id: str,
        *,
        project_id: str | None,
    ) -> str:
        poll_url = f"{REPLICATE_API_BASE}/predictions/{prediction_id}"
        headers = _auth_header(self.api_key)
        deadline = max(90.0, float(self._settings.vision_replicate_timeout_seconds))
        interval = max(0.5, self._settings.vision_replicate_poll_seconds)
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
                raise ReplicateScreenshotError("Sortie image vide.")
            if status in ("failed", "canceled"):
                raise ReplicateScreenshotError(
                    str(payload.get("error") or f"Statut {status}")
                )
            await asyncio.sleep(interval)
            elapsed += interval

        raise ReplicateScreenshotError("Délai Replicate image dépassé.")

    @staticmethod
    def _split_model_slug(slug: str) -> tuple[str, str]:
        parts = slug.strip().split("/", 1)
        if len(parts) != 2:
            raise ReplicateScreenshotError(f"Modèle Replicate invalide : {slug}")
        return parts[0], parts[1]
