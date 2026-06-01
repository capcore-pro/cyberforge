"""Tests routage ResearchAI — après Architect, avant DesignSystem."""

from __future__ import annotations

from unittest.mock import patch

from agents.pipeline_graph import (
    NODE_DESIGN_SYSTEM,
    PipelineState,
    _research_requested,
    _route_after_architect,
    _route_after_research,
    _route_after_template_ai,
)


def test_research_requested_default_on() -> None:
    state: PipelineState = {"research_enabled": None}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.research_enabled = True
        assert _research_requested(state) is True


def test_research_disabled() -> None:
    state: PipelineState = {"research_enabled": False}
    assert _research_requested(state) is False


def test_route_after_architect_to_research() -> None:
    state: PipelineState = {"research_enabled": True}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.research_enabled = True
        assert _route_after_architect(state) == "research"


def test_route_after_architect_skips_research() -> None:
    state: PipelineState = {"research_enabled": False}
    assert _route_after_architect(state) == NODE_DESIGN_SYSTEM


def test_route_after_research_to_design_system() -> None:
    state: PipelineState = {"generation_mode": "client_demo"}
    assert _route_after_research(state) == NODE_DESIGN_SYSTEM


def test_route_after_template_to_stitch() -> None:
    state: PipelineState = {"stitch_enabled": True}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.stitch_enabled = True
        assert _route_after_template_ai(state) == "stitch"


def test_route_after_template_to_content_when_no_stitch() -> None:
    state: PipelineState = {"stitch_enabled": False}
    assert _route_after_template_ai(state) == "content_ai"
