"""Tests aperçu — délégation pipeline TaskFlow."""

from tools.codegen_service import CodeGenerateResult
from tools.demo_pipeline import build_client_demo_document
from agents.demo_quality import preview_html_from_generation


def test_preview_matches_pipeline_html() -> None:
    import asyncio

    doc = asyncio.run(
        build_client_demo_document(
            "Réservation tables",
            project_type_label="App",
        )
    )
    gen = doc.generation
    preview = preview_html_from_generation(gen, title="App", user_prompt="Réservation")
    assert preview == doc.html
    assert "saas-shell" in preview
