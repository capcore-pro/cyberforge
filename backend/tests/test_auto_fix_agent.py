"""Tests AutoFixAI — repli template ArchitectAI et reprise BuilderAI vitrine."""

import asyncio
from unittest.mock import AsyncMock, patch

from agents.architect_agent import ArchitectPlan
from agents.auto_fix_agent import (
    AutoFixAgent,
    MAX_FIX_ATTEMPTS,
    needs_immediate_template_fallback,
)
from agents.bug_hunter_agent import BugHunterAgent, BugHuntReport, BugIssue
from agents.coremind_agent import (
    ComplexityLevel,
    CoreMindAnalysis,
    ProjectType,
    RecommendedTool,
)
from tools.codegen_service import CodeGenComplexity, CodeGenerateResult, GeneratedFile
from tools.demo_template_service import TEMPLATE_CRM, TEMPLATE_LANDING, TEMPLATE_TASKFLOW


def _bad_report() -> BugHuntReport:
    return BugHuntReport(
        ok=False,
        issues=[
            BugIssue(code="visible_source", message="React visible"),
        ],
    )


def _vitrine_plan() -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site vitrine",
        template=TEMPLATE_LANDING,
        template_label="Landing",
        rationale="test",
        complexity_score=4,
        complexity_label="Simple",
        market_price_min=800,
        market_price_max=2000,
        suggested_price_min=400,
        suggested_price_max=800,
        pricing_category="vitrine_next",
    )


def _saas_plan() -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SAAS_DASHBOARD,
        project_type_label="SaaS dashboard",
        template=TEMPLATE_TASKFLOW,
        template_label="TaskFlow",
        rationale="test",
        complexity_score=5,
        complexity_label="Moyenne",
        market_price_min=1000,
        market_price_max=3000,
        suggested_price_min=500,
        suggested_price_max=1200,
        pricing_category="application_web",
    )


def _crm_plan() -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.APPLICATION_WEB,
        project_type_label="Application web",
        template=TEMPLATE_CRM,
        template_label="CRM",
        rationale="test",
        complexity_score=5,
        complexity_label="Moyenne",
        market_price_min=1000,
        market_price_max=3000,
        suggested_price_min=500,
        suggested_price_max=1200,
        pricing_category="application_web",
    )


def _vitrine_analysis() -> CoreMindAnalysis:
    return CoreMindAnalysis(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site vitrine",
        recommended_tool=RecommendedTool.V0,
        tool_rationale="test",
        complexity=ComplexityLevel.MOYENNE,
        complexity_score=4,
        next_steps=[],
        summary="test",
    )


def test_needs_immediate_template_fallback_on_visible_source() -> None:
    assert needs_immediate_template_fallback(_bad_report())


def test_immediate_landing_fallback_without_plan() -> None:
    """Sans plan SaaS explicite → landing, pas TaskFlow."""
    with patch(
        "agents.auto_fix_agent.CodeGenService.generate_code",
        new_callable=AsyncMock,
    ) as mock_gen:
        agent = AutoFixAgent()
        result, attempts, report = asyncio.run(
            agent.repair(
                user_prompt="Restaurant demo",
                tier=CodeGenComplexity.MOYENNE,
                title="Restaurant",
                initial_report=_bad_report(),
            )
        )
        mock_gen.assert_not_called()

    assert attempts == 0
    assert result.provider == "cyberforge"
    assert result.model == "cyberforge-premium"
    assert "cf-premium-landing" in result.code
    assert "cf-preview:v3-premium-saas" not in result.code
    assert report.ok


def test_immediate_taskflow_for_explicit_saas_plan() -> None:
    with patch(
        "agents.auto_fix_agent.CodeGenService.generate_code",
        new_callable=AsyncMock,
    ) as mock_gen:
        agent = AutoFixAgent()
        result, attempts, _report = asyncio.run(
            agent.repair(
                user_prompt="SaaS gestion de tâches équipe",
                tier=CodeGenComplexity.MOYENNE,
                title="SaaS dashboard",
                initial_report=_bad_report(),
                plan=_saas_plan(),
            )
        )
        mock_gen.assert_not_called()

    assert attempts == 0
    assert "saas-shell" in result.code


def test_immediate_crm_fallback_for_crm_plan() -> None:
    with patch(
        "agents.auto_fix_agent.CodeGenService.generate_code",
        new_callable=AsyncMock,
    ) as mock_gen:
        agent = AutoFixAgent()
        result, attempts, report = asyncio.run(
            agent.repair(
                user_prompt="CRM contacts pipeline",
                tier=CodeGenComplexity.MOYENNE,
                title="CRM",
                initial_report=_bad_report(),
                plan=_crm_plan(),
            )
        )
        mock_gen.assert_not_called()

    assert attempts == 0
    assert "cf-premium-crm" in result.code
    assert report.ok


def test_vitrine_uses_builder_retry_not_taskflow() -> None:
    landing_html = (
        "<!DOCTYPE html><html><head><style>"
        + "body{margin:0;background:#0D0D0D;color:#fff;}"
        + "h1{font-size:2rem;}.hero{padding:2rem;}.nav{display:flex;}"
        + ".svc{margin:1rem;}.cta{background:#C9A84C;padding:1rem;}"
        + "</style></head><body><header class='nav'>Nav</header>"
        "<section class='hero'><h1>Vitrine</h1></section>"
        "<section class='svc'>Services</section></body></html>"
    )
    mock_gen = CodeGenerateResult(
        summary="landing retry",
        code=landing_html,
        files=[GeneratedFile(path="index.html", content=landing_html)],
        stack=["html"],
        model="builder-retry",
        provider="cyberforge",
    )

    with patch.object(
        AutoFixAgent,
        "_apply_vitrine_builder_retry",
        new_callable=AsyncMock,
        return_value=(mock_gen, 0, BugHuntReport(ok=True, html_bytes=100)),
    ) as mock_retry:
        agent = AutoFixAgent()
        result, attempts, report = asyncio.run(
            agent.repair(
                user_prompt="Site vitrine CapCore",
                tier=CodeGenComplexity.MOYENNE,
                title="CapCore",
                initial_report=_bad_report(),
                plan=_vitrine_plan(),
                analysis=_vitrine_analysis(),
            )
        )
        mock_retry.assert_awaited_once()

    assert attempts == 0
    assert "saas-shell" not in result.code
    assert report.ok


def test_repair_fallback_uses_architect_template_after_failed_attempts() -> None:
    """Échec LLM → repli CRM si plan CRM (pas TaskFlow systématique)."""
    minimal_html = "<!DOCTYPE html><html><head></head><body><p>ok</p></body></html>"
    bad_gen = CodeGenerateResult(
        summary="bad",
        code=minimal_html,
        files=[GeneratedFile(path="index.html", content=minimal_html)],
        stack=["html"],
        model="test",
        provider="test",
    )
    missing_css_report = BugHuntReport(
        ok=False,
        issues=[BugIssue(code="missing_css", message="peu de CSS")],
    )

    still_bad = BugHuntReport(
        ok=False,
        issues=[BugIssue(code="missing_css", message="peu de CSS")],
    )

    def analyze_side_effect(html: str) -> BugHuntReport:
        if "cf-premium-crm" in html:
            return BugHuntReport(ok=True, html_bytes=len(html.encode()))
        return still_bad

    with (
        patch(
            "agents.auto_fix_agent.CodeGenService.generate_code",
            new_callable=AsyncMock,
            return_value=bad_gen,
        ),
        patch(
            "agents.auto_fix_agent.preview_html_from_generation",
            return_value=minimal_html,
        ),
        patch.object(BugHunterAgent, "analyze_html", side_effect=analyze_side_effect),
    ):
        agent = AutoFixAgent()
        result, attempts, report = asyncio.run(
            agent.repair(
                user_prompt="CRM pipeline commercial",
                tier=CodeGenComplexity.MOYENNE,
                title="CRM",
                initial_report=missing_css_report,
                plan=_crm_plan(),
            )
        )

    assert attempts == MAX_FIX_ATTEMPTS
    assert result.provider == "cyberforge"
    assert "cf-premium-crm" in result.code
    assert report.ok
