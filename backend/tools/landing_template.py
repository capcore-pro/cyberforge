"""
Template landing — hero, features, CTA, footer.
"""

from __future__ import annotations

from tools.demo_template_gate import build_gated_html
from tools.premium_landing_page_html import LANDING_MARKER, build_premium_landing_html

TEMPLATE_ID = "landing"
MARKER = LANDING_MARKER

build_html = build_premium_landing_html


def build_gated_landing_html(
    password: str, *, title: str = "Démo Landing", **kwargs: object
) -> str:
    return build_gated_html(build_html, password, title=title, **kwargs)
