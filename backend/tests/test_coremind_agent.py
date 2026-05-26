"""Tests unitaires CoreMindAI."""

import pytest

from agents.coremind_agent import (
    ComplexityLevel,
    CoreMindAgent,
    ProjectType,
    RecommendedTool,
)


@pytest.mark.asyncio
async def test_analyze_saas_dashboard() -> None:
    agent = CoreMindAgent()
    result = await agent.analyze(
        "Je veux un SaaS de monitoring cybersécurité avec dashboard admin et auth"
    )
    assert result.project_type == ProjectType.SAAS_DASHBOARD
    assert result.recommended_tool in (
        RecommendedTool.V0,
        RecommendedTool.DEEPSEEK,
    )
    assert result.complexity in (
        ComplexityLevel.MOYENNE,
        ComplexityLevel.ELEVEE,
    )
    assert len(result.next_steps) >= 4


@pytest.mark.asyncio
async def test_analyze_landing_prefers_v0() -> None:
    agent = CoreMindAgent()
    result = await agent.analyze(
        "Créer une landing page marketing avec design UI moderne et tailwind"
    )
    assert result.project_type == ProjectType.SITE_WEB
    assert result.recommended_tool == RecommendedTool.V0


@pytest.mark.asyncio
async def test_empty_prompt_raises() -> None:
    agent = CoreMindAgent()
    with pytest.raises(ValueError, match="vide"):
        await agent.analyze("   ")
