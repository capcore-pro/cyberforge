"""Tests routage Playwright dans le pipeline (non bloquant)."""

from __future__ import annotations

from unittest.mock import patch

from agents.playwright_agent import PlaywrightReport
from agents.pipeline_graph import (
    PipelineState,
    _playwright_requested,
    _route_after_playwright,
    _route_after_testpilot,
)


def test_playwright_requested_default_on() -> None:
    state: PipelineState = {"playwright_enabled": None}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.playwright_enabled = True
        assert _playwright_requested(state) is True


def test_playwright_disabled() -> None:
    state: PipelineState = {"playwright_enabled": False}
    assert _playwright_requested(state) is False


def test_route_after_testpilot_to_playwright() -> None:
    class OkReport:
        ok = True

    state: PipelineState = {
        "testpilot_report": OkReport(),
        "playwright_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.playwright_enabled = True
        assert _route_after_testpilot(state) == "playwright"


def test_route_after_playwright_low_score_still_exports() -> None:
    state: PipelineState = {
        "playwright_report": PlaywrightReport(score=45, failed=["cta"]),
        "lighthouse_enabled": False,
    }
    assert _route_after_playwright(state) == "export"


def test_route_after_playwright_low_score_to_lighthouse() -> None:
    state: PipelineState = {
        "playwright_report": PlaywrightReport(score=45, failed=["cta"]),
        "lighthouse_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.lighthouse_enabled = True
        assert _route_after_playwright(state) == "lighthouse"
