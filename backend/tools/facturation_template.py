"""
Template facturation — tableau de factures, montants, statuts Payée / En attente / En retard.
"""

from __future__ import annotations

from tools.demo_template_gate import build_gated_html
from tools.premium_invoice_html import INVOICE_MARKER, build_premium_invoice_html

TEMPLATE_ID = "facturation"
MARKER = INVOICE_MARKER

build_html = build_premium_invoice_html


def build_gated_facturation_html(
    password: str, *, title: str = "Démo Facturation", **kwargs: object
) -> str:
    return build_gated_html(build_html, password, title=title, **kwargs)
