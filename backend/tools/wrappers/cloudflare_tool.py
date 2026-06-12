"""Wrapper Cloudflare Pages — Tool Framework V2."""

from __future__ import annotations

from security.agent_readiness import deploy_ready
from tools.base_tool import BaseTool, ToolRequest, ToolResult
from tools.export_cloudflare import CloudflareExportError, deploy_html_demo


class CloudflareTool(BaseTool):
    tool_id = "cloudflare_pages"
    name = "Cloudflare Pages"
    category = "deployment"

    def is_available(self) -> bool:
        return deploy_ready()

    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.action != "deploy":
            return ToolResult(
                success=False,
                error_message=f"Action inconnue : {request.action}",
            )

        payload = request.payload or {}
        html = str(payload.get("html") or "").strip()
        title = str(payload.get("title") or "CyberForge Demo").strip()
        project_type = str(payload.get("project_type") or "vitrine_next").strip()

        if not html:
            return ToolResult(success=False, error_message="html manquant")

        try:
            production_url, demo_token, demo_password, unlock_url = await deploy_html_demo(
                html=html,
                title=title,
                project_type=project_type,
            )
        except CloudflareExportError as exc:
            return ToolResult(success=False, error_message=str(exc))

        return ToolResult(
            success=True,
            output={
                "production_url": production_url,
                "demo_token": demo_token,
                "demo_password": demo_password,
                "unlock_url": unlock_url,
            },
        )
