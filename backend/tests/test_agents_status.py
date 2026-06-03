"""Tests GET /api/agents/status — prérequis clés API."""

from api.routes.agents_status import _agent_is_active


def test_research_active_with_brave_or_exa() -> None:
    assert _agent_is_active("research", {"brave_search": True}) is True
    assert _agent_is_active("research", {"exa": True}) is True
    assert _agent_is_active("research", {}) is False

def test_architect_always_active_in_pipeline() -> None:
    assert _agent_is_active("architect", {}) is True
