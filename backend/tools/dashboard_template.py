"""
Template dashboard — KPIs, graphiques barres/courbes, statistiques métier.
"""

from __future__ import annotations

from tools.demo_template_gate import build_gated_html
from tools.premium_dashboard_html import DASHBOARD_MARKER, build_premium_dashboard_html

TEMPLATE_ID = "dashboard"
MARKER = DASHBOARD_MARKER

build_html = build_premium_dashboard_html


def build_gated_dashboard_html(
    password: str, *, title: str = "Démo Dashboard", **kwargs: object
) -> str:
    return build_gated_html(build_html, password, title=title, **kwargs)
