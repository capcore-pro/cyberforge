"""Tests AutoFixAI — repli TaskFlow sans appel LLM."""

import asyncio
from unittest.mock import AsyncMock, patch

from agents.auto_fix_agent import AutoFixAgent, MAX_FIX_ATTEMPTS
from agents.bug_hunter_agent import BugHuntReport, BugIssue
from tools.codegen_service import CodeGenComplexity, CodeGenerateResult, GeneratedFile


def _bad_report() -> BugHuntReport:
    return BugHuntReport(
        ok=False,
        issues=[
            BugIssue(code="visible_source", message="React visible"),
        ],
    )


def test_repair_fallback_taskflow_after_failed_attempts() -> None:
    bad_html = '<!DOCTYPE html><html><head></head><body>export default function X(){}</body></html>'
    bad_gen = CodeGenerateResult(
        summary="bad",
        code=bad_html,
        files=[GeneratedFile(path="index.html", content=bad_html)],
        stack=["html"],
        model="test",
        provider="test",
    )

    with patch(
        "agents.auto_fix_agent.CodeGenService.generate_code",
        new_callable=AsyncMock,
        return_value=bad_gen,
    ):
        agent = AutoFixAgent()
        result, attempts, report = asyncio.run(
            agent.repair(
                user_prompt="Restaurant demo",
                tier=CodeGenComplexity.MOYENNE,
                title="Restaurant",
                initial_report=_bad_report(),
            )
        )

    assert attempts == MAX_FIX_ATTEMPTS
    assert result.provider == "cyberforge"
    assert result.model == "taskflow-premium"
    assert "saas-shell" in result.code
    assert report.ok
