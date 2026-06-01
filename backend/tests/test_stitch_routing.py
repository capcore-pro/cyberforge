"""Tests routage StitchAI dans le pipeline."""

from __future__ import annotations

from unittest.mock import patch

from agents.pipeline_graph import (
    PipelineState,
    _route_after_architect,
    _route_after_research,
    _route_after_stitch,
    _route_post_stitch,
    _stitch_requested,
)


def test_stitch_requested_default_on() -> None:
    state: PipelineState = {"stitch_enabled": None}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.stitch_enabled = True
        assert _stitch_requested(state) is True


def test_route_after_research_to_stitch() -> None:
    state: PipelineState = {"stitch_enabled": True}
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.stitch_enabled = True
        assert _route_after_research(state) == "stitch"


def test_route_after_stitch_to_coremind() -> None:
    state: PipelineState = {"generation_mode": "client_demo"}
    assert _route_after_stitch(state) == "coremind"


def test_route_after_architect_skips_to_stitch_without_research() -> None:
    state: PipelineState = {
        "research_enabled": False,
        "stitch_enabled": True,
    }
    with patch("agents.pipeline_graph.get_settings") as mock_settings:
        mock_settings.return_value.research_enabled = False
        mock_settings.return_value.stitch_enabled = True
        assert _route_after_architect(state) == "stitch"


def test_route_post_stitch_to_builder() -> None:
    state: PipelineState = {"generation_mode": "legacy"}
    assert _route_post_stitch(state) == "builder"
