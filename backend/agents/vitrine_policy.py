"""Politique vitrine HTML — pas de repli TaskFlow pour les sites vitrine."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import ProjectType

VITRINE_PROJECT_TYPES = frozenset(
    {
        ProjectType.SITE_WEB,
        ProjectType.LANDING_PAGE,
    }
)


def is_vitrine_html_project(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None = None,
) -> bool:
    """
    True pour les vitrines HTML (mode client_demo), pas pour vitrine_next (Next.js).
    """
    if (generation_mode or "client_demo") == "vitrine_next":
        return False
    if plan.project_type in VITRINE_PROJECT_TYPES:
        return True
    if plan.template == "landing":
        return True
    if plan.pricing_category == "vitrine_next":
        return True
    return False
