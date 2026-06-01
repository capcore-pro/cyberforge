"""Tests routage StitchAI — après TemplateAI, avant ContentAI."""

from __future__ import annotations

from unittest.mock import patch

from agents.pipeline_graph import (
    NODE_DESIGN_SYSTEM,
    PipelineState,
    _route_after_architect,
    _route_after_stitch,
    _route_after_template_ai,
    _route_post_stitch,
    _stitch_requested,
)


def test_stitch_requested_default_on() -> None:
    state: PipelineState = {"stitch_enabled": None}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.stitch_enabled = True
        assert _stitch_requested(state) is True


def test_route_after_template_to_stitch() -> None:
    state: PipelineState = {"stitch_enabled": True}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.stitch_enabled = True
        assert _route_after_template_ai(state) == "stitch"


def test_route_after_stitch_to_content_ai() -> None:
    state: PipelineState = {"generation_mode": "client_demo"}
    assert _route_after_stitch(state) == "content_ai"


def test_route_after_architect_to_design_system_without_research() -> None:
    state: PipelineState = {
        "research_enabled": False,
        "stitch_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.research_enabled = False
        mock_settings.return_value.stitch_enabled = True
        assert _route_after_architect(state) == NODE_DESIGN_SYSTEM


def test_route_post_stitch_to_builder() -> None:
    state: PipelineState = {"generation_mode": "legacy"}
    assert _route_post_stitch(state) == "builder"
