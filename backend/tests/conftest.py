"""Fixtures pytest partagées."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_content_ai_llm_enrichment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Évite les appels Claude réels pendant les tests unitaires."""
    monkeypatch.setenv("CONTENT_AI_ENRICH_LLM", "0")
