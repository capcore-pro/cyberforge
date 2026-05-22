"""Tests pipeline unique démo client."""

import asyncio

from tools.demo_pipeline import (
    INDEX_HTML_PATH,
    build_client_demo_document,
    wrap_demo_for_cloudflare,
)
from tools.demo_template_service import TEMPLATE_MARKERS, detect_template_from_prompt


def test_pipeline_single_index_html() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "Application de réservation pour restaurant italien",
            project_type_label="Application web",
        )
    )
    assert doc.generation.files[0].path == INDEX_HTML_PATH
    assert doc.html == doc.generation.code
    assert doc.template == "reservation"
    assert TEMPLATE_MARKERS[doc.template] in doc.html
    assert "export default" not in doc.html
    assert "Jean Dupont" in doc.html


def test_pipeline_landing_template() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "Landing page marketing avec hero et témoignages",
            project_type_label="Site web",
        )
    )
    assert doc.template == "landing"
    assert "cf-premium-landing" in doc.html


def test_pipeline_cloudflare_gate_has_toggle() -> None:
    doc = asyncio.run(
        build_client_demo_document("SaaS gestion tâches", project_type_label="SaaS")
    )
    gated = wrap_demo_for_cloudflare(doc, "test-pass", title="Démo")
    assert "cf-password-toggle" in gated
    assert TEMPLATE_MARKERS[doc.template] in gated


def test_detect_template_from_prompt_keywords() -> None:
    assert detect_template_from_prompt("facture TVA devis") == "invoice"
    assert detect_template_from_prompt("CRM pipeline contacts") == "crm"
    assert detect_template_from_prompt("CRM") == "crm"


def test_pipeline_crm_prompt_not_taskflow() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "CRM pour gérer mes contacts et le pipeline commercial",
            project_type_label="Application web",
        )
    )
    assert doc.template == "crm"
    assert "cf-premium-crm" in doc.html
    assert "saas-shell" not in doc.html
    assert "{contact.name}" not in doc.html
    assert "Finaliser la proposition client Acme Corp" not in doc.html


def test_client_demo_from_seed_dict_respects_prompt_crm() -> None:
    from tools.demo_pipeline import client_demo_from_seed_dict

    doc = client_demo_from_seed_dict(
        {
            "template": "taskflow",
            "title": "Mon CRM",
            "brand_name": "SalesHub",
            "tasks": [{"text": "Relancer les leads", "completed": False}],
        },
        prompt="CRM contacts pipeline",
        project_type_label="Application web",
    )
    assert doc.template == "crm"
    assert "cf-premium-crm" in doc.html
