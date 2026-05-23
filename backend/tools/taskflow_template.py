"""
Template TaskFlow — gestion de projet / SaaS (sidebar, tâches, stats).
"""

from __future__ import annotations

from tools.demo_template_gate import build_gated_html
from tools.premium_task_saas_html import (
    PREMIUM_PREVIEW_MARKER,
    build_premium_task_manager_html,
)

TEMPLATE_ID = "taskflow"
MARKER = "saas-shell"

build_html = build_premium_task_manager_html


def build_gated_taskflow_html(
    password: str, *, title: str = "Démo TaskFlow", **kwargs: object
) -> str:
    return build_gated_html(build_html, password, title=title, **kwargs)
