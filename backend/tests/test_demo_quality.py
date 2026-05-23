"""Tests aperçu — template premium aligné sur la seed du projet."""

import asyncio

from agents.demo_quality import preview_html_from_generation
from tools.demo_pipeline import build_client_demo_document


def test_preview_matches_crm_template() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "CRM contacts pipeline commercial",
            project_type_label="Application web",
        )
    )
    gen = doc.generation
    assert gen.demo_seed is not None
    assert doc.template == "crm"
    assert "cf-premium-crm" in doc.html

    preview = preview_html_from_generation(
        gen,
        title="Application web",
        user_prompt="CRM contacts pipeline commercial",
    )
    assert "cf-premium-crm" in preview
    assert "saas-shell" not in preview
    assert gen.demo_seed["brand_name"] in preview or doc.seed.brand_name in preview


def test_preview_matches_facturation_template() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "Application de facturation avec TVA et relances",
            project_type_label="Application web",
        )
    )
    assert doc.template == "facturation"
    preview = preview_html_from_generation(
        doc.generation,
        title="Application web",
        user_prompt="facturation TVA",
    )
    assert "cf-premium-invoice" in preview
    assert "En retard" in preview
