"""Wrapper Firecrawl — Tool Framework V2."""

from __future__ import annotations

from config import get_settings
from tools.base_tool import BaseTool, ToolRequest, ToolResult
from tools.firecrawl_client import FirecrawlError, firecrawl_scrape


class FirecrawlTool(BaseTool):
    tool_id = "firecrawl"
    name = "Firecrawl"
    category = "scraping"

    def is_available(self) -> bool:
        return get_settings().firecrawl_configured

    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.action not in ("scrape", "extract"):
            return ToolResult(
                success=False,
                error_message=f"Action inconnue : {request.action}",
            )

        payload = request.payload or {}
        url = str(payload.get("url") or "").strip()
        if not url:
            return ToolResult(success=False, error_message="url manquante")

        include_images = bool(payload.get("include_images", True))

        try:
            scraped = await firecrawl_scrape(url, include_images=include_images)
        except FirecrawlError as exc:
            return ToolResult(success=False, error_message=str(exc))

        return ToolResult(
            success=True,
            output={
                "url": scraped.url,
                "title": scraped.title,
                "markdown": scraped.markdown,
                "html": scraped.html,
                "image_count": len(scraped.images or []),
            },
        )
