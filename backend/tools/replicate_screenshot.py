"""
Capture d'écran HTML via l'API Replicate (VisionUI).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str
from cost_tracker import maybe_track_cost
from tools.vision_local_preview import VisionPreviewResult, local_html_preview

logger = logging.getLogger(__name__)

DEFAULT_REPLICATE_MODEL = "intelligent-utilities/html-to-image"
REPLICATE_API_BASE = "https://api.replicate.com/v1"


class ReplicateScreenshotError(Exception):
    """Erreur d'appel Replicate."""


def _auth_header(api_key: str) -> dict[str, str]:
    token = api_key.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return {"Authorization": f"Bearer {token}"}


def _extract_output_url(output: Any) -> str | None:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str) and first.startswith("http"):
            return first
    if isinstance(output, dict):
        for key in ("url", "image", "output"):
            val = output.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
    return None


class ReplicateScreenshotClient:
    """Client Replicate pour screenshot HTML → image."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def api_key(self) -> str:
        return plain_secret_str(self._settings.replicate_api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def model_slug(self) -> str:
        return self._settings.replicate_html_model or DEFAULT_REPLICATE_MODEL

    async def screenshot_html(
        self,
        html: str,
        *,
        title: str = "CyberForge",
        width: int | None = None,
        height: int | None = None,
        project_id: str | None = None,
        project_type: str | None = None,
    ) -> VisionPreviewResult:
        if not self.is_configured():
            return local_html_preview(html, title=title)

        w = width or self._settings.vision_screenshot_width
        h = height or self._settings.vision_screenshot_height
        trimmed = html.strip()
        if not trimmed:
            return local_html_preview(html, title=title)

        max_chars = max(10_000, self._settings.vision_html_max_chars)
        if len(trimmed) > max_chars:
            trimmed = trimmed[:max_chars] + "\n<!-- tronqué pour Replicate -->"

        input_payload: dict[str, Any] = {
            "html": trimmed,
            "width": w,
            "height": h,
        }

        try:
            url = await self._run_model_prediction(input_payload, project_id=project_id)
        except (ReplicateScreenshotError, httpx.HTTPError) as exc:
            logger.warning("Replicate VisionUI — %s, fallback HTML local", exc)
            result = local_html_preview(html, title=title)
            result.message = f"Replicate indisponible ({exc}) — {result.message}"
            return result

        if not url:
            result = local_html_preview(html, title=title)
            result.message = "Replicate sans URL image — rendu HTML local."
            return result

        await self._persist_replicate_image(
            url,
            project_id=project_id,
            project_type=project_type,
        )

        return VisionPreviewResult(
            source="replicate",
            screenshot_url=url,
            local_html=trimmed,
            message="Capture Replicate générée.",
        )

    async def _persist_replicate_image(
        self,
        image_url: str,
        *,
        project_id: str | None,
        project_type: str | None,
    ) -> None:
        from tools.media_library import try_save_generated_asset

        safe_pid = re.sub(r"[^\w.\-]", "_", (project_id or "unknown"))[:64]
        ptype = (project_type or "unknown").strip() or "unknown"
        await try_save_generated_asset(
            url=image_url,
            filename=f"replicate_{safe_pid}.png",
            project_id=project_id,
            source="generated",
            tags=["replicate", ptype],
        )

    async def _run_model_prediction(
        self,
        input_payload: dict[str, Any],
        *,
        project_id: str | None = None,
    ) -> str:
        owner, name = self._split_model_slug(self.model_slug)
        create_url = f"{REPLICATE_API_BASE}/models/{owner}/{name}/predictions"
        timeout = httpx.Timeout(self._settings.vision_replicate_timeout_seconds)
        headers = {
            **_auth_header(self.api_key),
            "Content-Type": "application/json",
            "Prefer": f"wait={int(min(60, self._settings.vision_replicate_timeout_seconds))}",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                create_url,
                json={"input": input_payload},
                headers=headers,
            )

            if response.status_code == 422:
                body = response.json()
                detail = body.get("detail") if isinstance(body, dict) else body
                raise ReplicateScreenshotError(f"Entrée invalide: {detail}")

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
                raise ReplicateScreenshotError("Prédiction réussie sans URL de sortie.")

            if status in ("failed", "canceled"):
                raise ReplicateScreenshotError(
                    str(payload.get("error") or f"Statut {status}")
                )

            prediction_id = payload.get("id")
            if not prediction_id:
                raise ReplicateScreenshotError("Réponse Replicate sans id de prédiction.")

            return await self._poll_prediction(
                client,
                str(prediction_id),
                project_id=project_id,
            )

    async def _poll_prediction(
        self,
        client: httpx.AsyncClient,
        prediction_id: str,
        *,
        project_id: str | None = None,
    ) -> str:
        poll_url = f"{REPLICATE_API_BASE}/predictions/{prediction_id}"
        headers = _auth_header(self.api_key)
        deadline = self._settings.vision_replicate_timeout_seconds
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
                raise ReplicateScreenshotError("Sortie Replicate vide.")

            if status in ("failed", "canceled"):
                raise ReplicateScreenshotError(
                    str(payload.get("error") or f"Statut {status}")
                )

            await asyncio.sleep(interval)
            elapsed += interval

        raise ReplicateScreenshotError("Délai Replicate dépassé.")

    @staticmethod
    def _split_model_slug(slug: str) -> tuple[str, str]:
        parts = slug.strip().split("/", 1)
        if len(parts) != 2:
            raise ReplicateScreenshotError(f"Modèle Replicate invalide : {slug}")
        return parts[0], parts[1]
