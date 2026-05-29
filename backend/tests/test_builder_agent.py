"""Tests BuilderAI — routage v0 vs DeepSeek (sous CoreMindAI)."""

from agents.architect_agent import ArchitectPlan
from agents.builder_agent import BuilderAgent, BuilderProvider
from agents.coremind_agent import (
    ComplexityLevel,
    CoreMindAnalysis,
    ProjectType,
    RecommendedTool,
)


def _plan(project_type: ProjectType, template: str = "taskflow") -> ArchitectPlan:
    return ArchitectPlan(
        project_type=project_type,
        project_type_label="Test",
        template=template,
        template_label=template,
        rationale="test",
        complexity_score=5,
        complexity_label="Moyenne",
        market_price_min=1500,
        market_price_max=3000,
        suggested_price_min=600,
        suggested_price_max=1200,
        pricing_category="application_web",
    )


def _analysis(
    tool: RecommendedTool = RecommendedTool.V0,
    complexity: ComplexityLevel = ComplexityLevel.MOYENNE,
) -> CoreMindAnalysis:
    return CoreMindAnalysis(
        project_type=ProjectType.SAAS_DASHBOARD,
        project_type_label="SaaS",
        recommended_tool=tool,
        tool_rationale="test",
        complexity=complexity,
        complexity_score=5,
        next_steps=[],
        summary="test",
    )


def test_select_v0_for_react_ui_prompt() -> None:
    agent = BuilderAgent()
    decision = agent.select_provider(
        "Créer une app Next.js avec React et Tailwind",
        plan=_plan(ProjectType.APPLICATION_WEB),
        analysis=_analysis(RecommendedTool.V0),
    )
    assert decision.provider == BuilderProvider.V0


def test_select_deepseek_when_coremind_orders_it() -> None:
    agent = BuilderAgent()
    decision = agent.select_provider(
        "Landing page marketing",
        plan=_plan(ProjectType.LANDING_PAGE),
        analysis=_analysis(RecommendedTool.DEEPSEEK),
    )
    assert decision.provider == BuilderProvider.DEEPSEEK


def test_select_deepseek_for_api_backend() -> None:
    agent = BuilderAgent()
    decision = agent.select_provider(
        "API REST FastAPI avec PostgreSQL",
        plan=_plan(ProjectType.API_BACKEND),
        analysis=_analysis(RecommendedTool.V0),
    )
    assert decision.provider == BuilderProvider.DEEPSEEK


def test_build_fallback_without_v0_key(monkeypatch) -> None:
    import asyncio

    from config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "v0_api_key", None)

    agent = BuilderAgent(settings)
    result = asyncio.run(
        agent.build(
            "Dashboard React",
            plan=_plan(ProjectType.APPLICATION_WEB),
            analysis=_analysis(),
            settings=settings,
        )
    )
    assert result.fallback_to_coremind is True
    assert result.generation is None
