"""Tests pipeline unique démo client."""

import asyncio

from tools.demo_pipeline import (
    INDEX_HTML_PATH,
    build_client_demo_document,
    wrap_demo_for_cloudflare,
)


def test_pipeline_single_index_html() -> None:
    doc = asyncio.run(
        build_client_demo_document(
            "Application de réservation pour restaurant italien",
            project_type_label="Application web",
        )
    )
    assert doc.generation.files[0].path == INDEX_HTML_PATH
    assert doc.html == doc.generation.code
    assert "saas-shell" in doc.html
    assert "export default" not in doc.html
    assert any("réservation" in t[0].lower() for t in doc.seed.tasks)


def test_pipeline_cloudflare_gate_has_toggle() -> None:
    doc = asyncio.run(
        build_client_demo_document("SaaS gestion tâches", project_type_label="SaaS")
    )
    gated = wrap_demo_for_cloudflare(doc, "test-pass", title="Démo")
    assert "cf-password-toggle" in gated
    assert "saas-shell" in gated
