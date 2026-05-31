"""Tests routage Playwright dans le pipeline."""

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


def test_route_after_playwright_low_score_to_autofix() -> None:
    state: PipelineState = {
        "playwright_report": PlaywrightReport(score=45, failed=["cta"]),
        "playwright_autofix_loops": 0,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.playwright_pass_threshold = 70
        assert _route_after_playwright(state) == "autofix"


def test_route_after_playwright_high_score_to_export() -> None:
    state: PipelineState = {
        "playwright_report": PlaywrightReport(score=85, passed=["page_load_200"]),
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.playwright_pass_threshold = 70
        assert _route_after_playwright(state) == "export"
