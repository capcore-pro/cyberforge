"""Repli template premium aligné sur le plan ArchitectAI — jamais TaskFlow par défaut."""

from __future__ import annotations

import logging
from dataclasses import replace

from tools.demo_template_service import (
    TEMPLATE_LABELS,
    TEMPLATE_MODEL,
    TEMPLATE_PROVIDER,
    TEMPLATE_TASKFLOW,
    build_html_from_seed,
    heuristic_demo_seed,
    normalize_template_id,
)
from tools.standalone_demo_html import build_task_manager_standalone_html

logger = logging.getLogger(__name__)

TEMPLATE_FALLBACK_MODEL = TEMPLATE_MODEL
TEMPLATE_FALLBACK_PROVIDER = TEMPLATE_PROVIDER


def resolve_fallback_template(
    *,
    template: str | None,
    project_type_label: str = "",
) -> str:
    """
    TaskFlow uniquement pour template taskflow explicite.
    Sinon landing par défaut (vitrines / projets génériques).
    """
    normalized = normalize_template_id(template or TEMPLATE_TASKFLOW)
    if normalized == TEMPLATE_TASKFLOW:
        label = (project_type_label or "").lower()
        if "saas" not in label and "taskflow" not in label and "tâche" not in label:
            return "landing"
    return normalized


def build_template_fallback_html(
    *,
    user_prompt: str,
    title: str,
    template: str | None = None,
) -> tuple[str, str]:
    """
    Produit le HTML de repli et un libellé template pour les logs.
    Retourne (html, template_id).
    """
    template_id = resolve_fallback_template(
        template=template,
        project_type_label=title,
    )
    if template_id == TEMPLATE_TASKFLOW:
        html = build_task_manager_standalone_html(
            title=title,
            subtitle=f"Démo interactive — {TEMPLATE_LABELS.get(template_id, template_id)} (repli qualité).",
            sources=user_prompt[:8000],
        )
        logger.info("[TemplateFallback] TaskFlow SaaS | template=%s", template_id)
        return html, template_id

    seed = heuristic_demo_seed(user_prompt, project_type_label=title)
    html = build_html_from_seed(seed, force_template=template_id)
    logger.info("[TemplateFallback] template premium | template=%s", template_id)
    return html, template_id
