"""Validation souple du client_name dans SupervisorAI.validate_html."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "supervisor_ai_client_name_test",
    _BACKEND / "agents" / "supervisor_ai.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

SupervisorAI = _mod.SupervisorAI
_client_name_matches_text = _mod._client_name_matches_text


def test_client_name_matches_case_insensitive_full_string() -> None:
    assert _client_name_matches_text(
        "ecole de voile",
        "<h1>École de Voile</h1>",
    )


def test_client_name_matches_partial_words_in_html() -> None:
    assert _client_name_matches_text(
        "ecole de voile",
        "<title>École De Voile — Cours nautiques</title><p>Bienvenue</p>",
    )


def test_client_name_matches_two_words_only() -> None:
    assert _client_name_matches_text(
        "ecole de voile atlantique",
        "<h1>École de Voile</h1>",
    )


def test_client_name_rejects_unrelated_html() -> None:
    assert not _client_name_matches_text(
        "ecole de voile",
        "<h1>Boulangerie du Port</h1>",
    )


def test_client_name_single_word() -> None:
    assert _client_name_matches_text("Dupont", "<h1>Plomberie Dupont</h1>")
    assert not _client_name_matches_text("Dupont", "<h1>Plomberie Martin</h1>")


@pytest.mark.asyncio
async def test_validate_html_accepts_title_case_variants() -> None:
    supervisor = SupervisorAI()
    html = (
        "<html><head><title>École De Voile</title>"
        "<style>:root{--color-primary:#112233;}</style></head>"
        "<body><header><nav></nav></header>"
        "<section class='hero' style='min-height:60vh'><h1>École De Voile</h1>"
        "<img class='pexels-inject'><img class='pexels-inject'><img class='pexels-inject'>"
        "</section><section></section><section></section><footer></footer>"
        "</body></html>"
    )
    # Pad to pass minimum length
    html = html + (" " * 2800)
    brief = {
        "project_type": "vitrine",
        "client_name": "ecole de voile",
        "couleur_primaire": "#112233",
    }
    result = await supervisor.validate_html(html, brief)
    name_errors = [e for e in result["errors"] if "client_name" in e]
    assert name_errors == []
