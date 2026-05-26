"""Tests VisionUI — fallback HTML local."""

import asyncio

from agents.visionui_agent import VisionUIAgent
from config import get_settings


def test_capture_local_without_replicate_key(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "replicate_api_key", None)
    agent = VisionUIAgent(settings)
    html = "<!DOCTYPE html><html><body><h1>Test</h1></body></html>"
    result = asyncio.run(agent.capture(html, title="Demo", settings=settings))
    assert result.preview_source == "local"
    assert result.preview.local_html == html
    assert result.screenshot_url is None
