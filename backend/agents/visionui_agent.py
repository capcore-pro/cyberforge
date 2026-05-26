"""
VisionUI — aperçu visuel (screenshot Replicate ou rendu HTML local).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from config import Settings
from tools.replicate_screenshot import ReplicateScreenshotClient
from tools.vision_local_preview import VisionPreviewResult, local_html_preview

logger = logging.getLogger(__name__)


class VisionUIRunResult(BaseModel):
    """Résultat VisionUI pour le pipeline."""

    agent_id: str = "visionui"
    agent_name: str = "VisionUI"
    preview: VisionPreviewResult
    screenshot_url: str | None = None
    preview_source: str = Field(description="replicate | local")


class VisionUIAgent(BaseAgent):
    """Génère un aperçu screenshot du HTML via Replicate, sinon rendu local."""

    @property
    def agent_id(self) -> str:
        return "visionui"

    @property
    def name(self) -> str:
        return "VisionUI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = kwargs.get("html") or prompt
        title = str(kwargs.get("title") or "Aperçu")
        result = await self.capture(str(html), title=title)
        return result.model_dump_json()

    async def capture(
        self,
        html: str,
        *,
        title: str = "Aperçu CyberForge",
        settings: Settings | None = None,
    ) -> VisionUIRunResult:
        resolved = settings or self._settings
        client = ReplicateScreenshotClient(resolved)

        if client.is_configured():
            preview = await client.screenshot_html(html, title=title)
        else:
            logger.info("REPLICATE_API_KEY absente — rendu HTML local VisionUI")
            preview = local_html_preview(html, title=title)
            preview.message = "REPLICATE_API_KEY absente — rendu HTML local."

        return VisionUIRunResult(
            preview=preview,
            screenshot_url=preview.screenshot_url,
            preview_source=preview.source,
        )
