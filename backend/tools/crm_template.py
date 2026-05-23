"""
Template CRM — contacts, pipeline commercial, fiches clients.
Statuts : Prospect, Client, Perdu.
"""

from __future__ import annotations

from tools.demo_template_gate import build_gated_html
from tools.premium_crm_html import CRM_MARKER, build_premium_crm_html

TEMPLATE_ID = "crm"
MARKER = CRM_MARKER

build_html = build_premium_crm_html


def build_gated_crm_html(password: str, *, title: str = "Démo CRM", **kwargs: object) -> str:
    return build_gated_html(build_html, password, title=title, **kwargs)
