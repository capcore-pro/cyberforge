"""Tests aperçu — TaskFlow premium via seed du projet."""

import asyncio

from agents.demo_quality import preview_html_from_generation
from tools.demo_pipeline import build_client_demo_document


def test_preview_always_taskflow_with_project_seed() -> None:
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
    assert "saas-shell" in preview
    assert "cf-premium-crm" not in preview
    assert gen.demo_seed["brand_name"] in preview or doc.seed.brand_name in preview
