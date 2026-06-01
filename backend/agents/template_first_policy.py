"""
Politique template-first HTML — tous types livrables en assemblage (pas LLM from scratch).
"""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import ProjectType
from agents.vitrine_policy import is_vitrine_html_project
from tools.sector_template_catalog import is_template_first_pricing_category


def is_template_first_html_project(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None = None,
) -> bool:
    """
    True si le pipeline doit charger template sectoriel + ContentAI + Builder assemble.
    Exclut real_app (React/TS généré) et vitrine_next (Next.js déployé).
    """
    if plan.project_type == ProjectType.EXTENSION_NAVIGATEUR:
        return False
    mode = (generation_mode or "client_demo").strip().lower()
    if mode == "real_app":
        return False
    if mode == "vitrine_next":
        return False
    if is_vitrine_html_project(plan, generation_mode=generation_mode):
        return True
    category = (getattr(plan, "pricing_category", None) or "").strip().lower()
    if is_template_first_pricing_category(category):
        return True
    pt = plan.project_type.value if hasattr(plan.project_type, "value") else str(plan.project_type)
    if pt == "application_desktop" and mode == "client_demo":
        return True
    if mode == "client_demo" and category in (
        "ecommerce",
        "site_reservation",
        "application_web",
        "application_desktop",
    ):
        return True
    return False
