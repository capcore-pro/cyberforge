"""
TemplateFirstBuilder — responsabilité unique : livrer un HTML depuis le catalogue.

Ne délègue pas à v0/DeepSeek pour les modes client_demo / vitrine_shell.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import CoreMindAnalysis
from agents.template_first_policy import is_template_first_html_project
from agents.vitrine_policy import is_vitrine_html_project
from core.agent_contract import AgentContractError, AgentResult, require_ok
from core.template_engine import render_template
from core.template_registry import (
    TemplateDefinition,
    is_template_first_mode,
    require_template_for_plan,
)

logger = logging.getLogger(__name__)


def must_use_template_first(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None,
) -> bool:
    """Décision non négociable : ces modes interdisent le HTML LLM libre."""
    mode = (generation_mode or "client_demo").strip().lower()
    if mode == "real_app":
        return False
    if mode == "vitrine_next":
        return False
    if is_template_first_html_project(plan, generation_mode=generation_mode):
        return True
    if is_vitrine_html_project(plan, generation_mode=generation_mode):
        return True
    if mode == "client_demo":
        return True
    return is_template_first_mode(mode)


def resolve_template_definition(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None,
) -> TemplateDefinition:
    """Valide le choix ArchitectAI contre le catalogue."""
    mode = (generation_mode or "client_demo").strip().lower()
    pt = plan.project_type.value if hasattr(plan.project_type, "value") else str(plan.project_type)
    template_id = plan.template
    if is_vitrine_html_project(plan, generation_mode=generation_mode):
        if template_id not in ("landing", "reservation"):
            template_id = "landing"
    return require_template_for_plan(
        template_id=template_id,
        project_type=pt,
        generation_mode=mode,
    )


async def build_template_first(
    *,
    user_prompt: str,
    plan: ArchitectPlan,
    analysis: CoreMindAnalysis,
    research_brief: Any | None = None,
    generation_mode: str | None = None,
    project_id: str | None = None,
    design_system: Any | None = None,
    sector_template_html: str | None = None,
) -> AgentResult[tuple[Any, str]]:
    """
    Construit generation + preview_html via le moteur template.
    Lève ou retourne failure — jamais de HTML générique silencieux.
    """
    del analysis  # réservé aux extensions (slots LLM copy-only)
    if not must_use_template_first(plan, generation_mode=generation_mode):
        return AgentResult.failure(
            agent_id="template_first",
            agent_name="TemplateFirstBuilder",
            code="not_applicable",
            message="Ce mode requiert le pipeline LLM (real_app).",
        )

    try:
        definition = resolve_template_definition(plan, generation_mode=generation_mode)
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id="template_first",
            agent_name="TemplateFirstBuilder",
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )

    logger.info(
        "[TemplateFirst] rendu | template=%s | kind=%s | project_type=%s",
        definition.id,
        definition.render_kind,
        plan.project_type_label,
    )

    result = await render_template(
        definition,
        plan=plan,
        user_prompt=user_prompt,
        research_brief=research_brief,
        project_id=project_id,
        design_system=design_system,
        sector_template_html=sector_template_html,
    )
    return result
