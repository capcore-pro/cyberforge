"""Tests ArchitectAI."""

import pytest

from agents.architect_agent import ArchitectAgent
from agents.coremind_agent import ProjectType
from tools.demo_template_service import TEMPLATE_CRM, TEMPLATE_LANDING


@pytest.mark.asyncio
async def test_architect_detects_crm_template() -> None:
    agent = ArchitectAgent()
    plan, analysis = await agent.plan_with_analysis(
        "Je veux un CRM pour gérer mes contacts clients et le pipeline commercial"
    )
    assert plan.template == TEMPLATE_CRM
    assert plan.project_type in (ProjectType.SAAS_DASHBOARD, ProjectType.APPLICATION_WEB)
    assert analysis.complexity_score >= 1


@pytest.mark.asyncio
async def test_architect_landing_hint() -> None:
    agent = ArchitectAgent()
    plan, _ = await agent.plan_with_analysis(
        "Landing page marketing avec hero et CTA pour startup",
        project_type_hint=ProjectType.LANDING_PAGE,
    )
    assert plan.template in (TEMPLATE_LANDING, "taskflow", "landing")
    assert "Landing" in plan.project_type_label or plan.project_type == ProjectType.LANDING_PAGE
