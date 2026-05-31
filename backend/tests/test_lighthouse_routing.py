"""Tests routage Lighthouse dans le pipeline."""

from __future__ import annotations

from unittest.mock import patch

from agents.lighthouse_agent import LighthouseReport
from agents.pipeline_graph import (
    PipelineState,
    _lighthouse_requested,
    _route_after_lighthouse,
    _route_after_playwright,
    _route_after_testpilot,
)


def test_lighthouse_requested_default_on() -> None:
    state: PipelineState = {"lighthouse_enabled": None}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.lighthouse_enabled = True
        assert _lighthouse_requested(state) is True


def test_lighthouse_disabled() -> None:
    state: PipelineState = {"lighthouse_enabled": False}
    assert _lighthouse_requested(state) is False


def test_route_after_playwright_to_lighthouse() -> None:
    class OkReport:
        ok = True
        skipped = False
        score = 85

    state: PipelineState = {
        "playwright_report": OkReport(),
        "lighthouse_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.lighthouse_enabled = True
        assert _route_after_playwright(state) == "lighthouse"


def test_route_after_lighthouse_low_score_to_autofix() -> None:
    state: PipelineState = {
        "lighthouse_report": LighthouseReport(score_global=45, recommendations=["seo"]),
        "lighthouse_autofix_loops": 0,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.lighthouse_pass_threshold = 70
        assert _route_after_lighthouse(state) == "autofix"


def test_route_after_lighthouse_high_score_to_export() -> None:
    state: PipelineState = {
        "lighthouse_report": LighthouseReport(
            score_global=85,
            performance=80,
            seo=90,
            accessibility=85,
            best_practices=85,
            ok=True,
        ),
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.lighthouse_pass_threshold = 70
        assert _route_after_lighthouse(state) == "export"


def test_route_after_testpilot_skip_playwright_to_lighthouse() -> None:
    class OkReport:
        ok = True

    state: PipelineState = {
        "testpilot_report": OkReport(),
        "playwright_enabled": False,
        "lighthouse_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.playwright_enabled = False
        mock_settings.return_value.lighthouse_enabled = True
        assert _route_after_testpilot(state) == "lighthouse"
