"""
VisionUI — enrichissement toolbox (photos, icônes, illustrations) puis aperçu Replicate ou local.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from config import Settings
from tools.replicate_screenshot import ReplicateScreenshotClient
from tools.vision_local_preview import VisionPreviewResult, local_html_preview
from tools.vision_toolbox_enricher import VisionEnrichStats, enrich_html_with_toolbox

if TYPE_CHECKING:
    from agents.architect_agent import ArchitectPlan

logger = logging.getLogger(__name__)


class VisionUIRunResult(BaseModel):
    """Résultat VisionUI pour le pipeline."""

    agent_id: str = "visionui"
    agent_name: str = "VisionUI"
    preview: VisionPreviewResult
    screenshot_url: str | None = None
    preview_source: str = Field(description="replicate | local")
    enrich_stats: VisionEnrichStats | None = None


class VisionUIAgent(BaseAgent):
    """Enrichit le HTML via toolbox puis capture screenshot (Replicate ou local)."""

    @property
    def agent_id(self) -> str:
        return "visionui"

    @property
    def name(self) -> str:
        return "VisionUI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = kwargs.get("html") or prompt
        title = str(kwargs.get("title") or "Aperçu")
        plan = kwargs.get("architect_plan")
        result = await self.capture(
            str(html),
            title=title,
            architect_plan=plan,
            prompt=kwargs.get("prompt") or prompt,
            project_id=kwargs.get("project_id"),
            project_type=kwargs.get("project_type"),
        )
        return result.model_dump_json()

    async def capture(
        self,
        html: str,
        *,
        title: str = "Aperçu CyberForge",
        settings: Settings | None = None,
        project_id: str | None = None,
        project_type: str | None = None,
        architect_plan: ArchitectPlan | None = None,
        prompt: str | None = None,
    ) -> VisionUIRunResult:
        resolved = settings or self._settings

        enriched_html, enrich_stats = await enrich_html_with_toolbox(
            html,
            plan=architect_plan,
            prompt=prompt,
            settings=resolved,
            project_id=project_id,
        )

        client = ReplicateScreenshotClient(resolved)
        if client.is_configured():
            preview = await client.screenshot_html(
                enriched_html,
                title=title,
                project_id=project_id,
                project_type=project_type,
            )
        else:
            logger.info("REPLICATE_API_KEY absente — rendu HTML local VisionUI")
            preview = local_html_preview(enriched_html, title=title)
            preview.message = "REPLICATE_API_KEY absente — rendu HTML local."

        if enrich_stats.tags:
            sources = ", ".join(enrich_stats.tags)
            preview.message = (
                f"{preview.message or 'Capture'} — médias toolbox : {sources}."
            ).strip()

        return VisionUIRunResult(
            preview=preview,
            screenshot_url=preview.screenshot_url,
            preview_source=preview.source,
            enrich_stats=enrich_stats,
        )
