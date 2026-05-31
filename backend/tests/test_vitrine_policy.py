"""Tests politique vitrine — pas de TaskFlow."""

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import ProjectType
from agents.vitrine_policy import is_vitrine_html_project


def _plan(
    project_type: ProjectType = ProjectType.SITE_WEB,
    template: str = "landing",
    pricing_category: str = "vitrine_next",
) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=project_type,
        project_type_label="Site vitrine",
        template=template,
        template_label=template,
        rationale="test",
        complexity_score=4,
        complexity_label="Simple",
        market_price_min=800,
        market_price_max=2000,
        suggested_price_min=400,
        suggested_price_max=800,
        pricing_category=pricing_category,
    )


def test_site_web_is_vitrine_html() -> None:
    assert is_vitrine_html_project(_plan())


def test_vitrine_next_mode_excluded() -> None:
    assert not is_vitrine_html_project(_plan(), generation_mode="vitrine_next")


def test_saas_dashboard_not_vitrine() -> None:
    plan = _plan(
        project_type=ProjectType.SAAS_DASHBOARD,
        template="taskflow",
        pricing_category="application_web",
    )
    assert not is_vitrine_html_project(plan)
