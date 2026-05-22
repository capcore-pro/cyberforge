"""Tests AutoFixAI — repli TaskFlow immédiat et après échecs LLM."""

import asyncio
from unittest.mock import AsyncMock, patch

from agents.auto_fix_agent import (
    AutoFixAgent,
    MAX_FIX_ATTEMPTS,
    needs_immediate_taskflow_fallback,
)
from agents.bug_hunter_agent import BugHunterAgent, BugHuntReport, BugIssue
from tools.codegen_service import CodeGenComplexity, CodeGenerateResult, GeneratedFile


def _bad_report() -> BugHuntReport:
    return BugHuntReport(
        ok=False,
        issues=[
            BugIssue(code="visible_source", message="React visible"),
        ],
    )


def test_needs_immediate_taskflow_on_visible_source() -> None:
    assert needs_immediate_taskflow_fallback(_bad_report())


def test_immediate_taskflow_without_llm_calls() -> None:
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
    assert result.model == "taskflow-premium"
    assert "saas-shell" in result.code
    assert report.ok


def test_repair_fallback_taskflow_after_failed_attempts() -> None:
    """missing_css seul : LLM retenté jusqu'à épuisement, puis TaskFlow."""
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
        if "saas-shell" in html:
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
                user_prompt="Restaurant demo",
                tier=CodeGenComplexity.MOYENNE,
                title="Restaurant",
                initial_report=missing_css_report,
            )
        )

    assert attempts == MAX_FIX_ATTEMPTS
    assert result.provider == "cyberforge"
    assert result.model == "taskflow-premium"
    assert "saas-shell" in result.code
    assert report.ok
