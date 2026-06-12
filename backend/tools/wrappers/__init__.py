"""Wrappers Tool Framework — outils pipeline V2."""

from __future__ import annotations

from config import get_settings, plain_secret_str
from security.agent_readiness import (
    anthropic_ready,
    brevo_ready,
    replicate_ready,
)
from tools.base_tool import BaseTool
from tools.wrappers.cloudflare_tool import CloudflareTool
from tools.wrappers.firecrawl_tool import FirecrawlTool
from tools.wrappers.pexels_tool import PexelsTool

_WRAPPER_INSTANCES: dict[str, BaseTool] = {
    "pexels": PexelsTool(),
    "cloudflare_pages": CloudflareTool(),
    "firecrawl": FirecrawlTool(),
}


def get_tool_wrapper(tool_id: str) -> BaseTool | None:
    return _WRAPPER_INSTANCES.get(tool_id)


def is_tool_available(tool_id: str) -> bool:
    wrapper = get_tool_wrapper(tool_id)
    if wrapper is not None:
        return wrapper.is_available()

    key = (tool_id or "").strip()
    if key == "anthropic_api":
        return anthropic_ready()
    if key == "openai_api":
        return bool(plain_secret_str(get_settings().openai_api_key))
    if key == "brevo":
        return brevo_ready()
    if key == "replicate":
        return replicate_ready()
    if key == "stripe_js":
        return True
    return False


__all__ = [
    "CloudflareTool",
    "FirecrawlTool",
    "PexelsTool",
    "get_tool_wrapper",
    "is_tool_available",
]
