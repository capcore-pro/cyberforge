"""Tests routage ResearchAI dans le pipeline."""

from __future__ import annotations

from unittest.mock import patch

from agents.pipeline_graph import (
    PipelineState,
    _research_requested,
    _route_after_architect,
    _route_after_research,
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


def test_route_after_research_to_coremind() -> None:
    state: PipelineState = {"generation_mode": "client_demo"}
    assert _route_after_research(state) == "coremind"


def test_route_after_research_to_builder_legacy_mode() -> None:
    state: PipelineState = {"generation_mode": "legacy_mode"}
    assert _route_after_research(state) == "builder"
