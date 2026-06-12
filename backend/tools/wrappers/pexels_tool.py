"""Wrapper Pexels — Tool Framework V2."""

from __future__ import annotations

from config import get_settings
from tools.base_tool import BaseTool, ToolRequest, ToolResult
from tools.toolbox_media import search_toolbox_photos


class PexelsTool(BaseTool):
    tool_id = "pexels"
    name = "Pexels"
    category = "media"

    def is_available(self) -> bool:
        return get_settings().pexels_configured

    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.action != "search":
            return ToolResult(
                success=False,
                error_message=f"Action inconnue : {request.action}",
            )

        payload = request.payload or {}
        query = str(payload.get("query") or "").strip()
        if not query:
            return ToolResult(success=False, error_message="query manquante")

        count = int(payload.get("count") or payload.get("per_page") or 6)
        secteur = payload.get("secteur")
        if secteur is not None:
            secteur = str(secteur)

        effective_query, photos = await search_toolbox_photos(
            query,
            secteur=secteur,
            per_page=max(1, min(count, 20)),
        )
        return ToolResult(
            success=True,
            output={
                "query": effective_query,
                "count": len(photos),
                "photos": [p.model_dump() for p in photos],
            },
        )
