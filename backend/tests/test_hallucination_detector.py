"""Tests HallucinationDetector — Volume 8 Module 4."""

from __future__ import annotations

from agents.hallucination_detector import HallucinationDetector


def test_detects_generic_patterns() -> None:
    html = (
        "<html><body><h1>[NOM] Boulangerie Dupont</h1>"
        "<p style='color:#d4a843'>Lorem ipsum dolor sit amet.</p>"
        "</body></html>"
    )
    brief = {"client_name": "Boulangerie Dupont", "couleur_primaire": "#d4a843"}

    result = HallucinationDetector().detect(html=html, brief=brief)

    assert result["hallucination_free"] is False
    assert len(result["issues"]) == 2
    assert result["severity"] == "medium"
    assert result["score"] == 60
    assert any("Pattern générique" in issue for issue in result["issues"])


def test_clean_html_passes_detection() -> None:
    brief = {
        "client_name": "Boulangerie Dupont",
        "couleur_primaire": "#d4a843",
    }
    html = (
        "<html><head><title>Boulangerie Dupont</title></head>"
        "<body style='color:#d4a843'>"
        "<h1>Boulangerie Dupont</h1>"
        "<p>Artisan boulanger à Lyon depuis 1987.</p>"
        "</body></html>"
    )

    result = HallucinationDetector().detect(html=html, brief=brief)

    assert result["hallucination_free"] is True
    assert result["severity"] == "none"
    assert result["score"] == 100
    assert result["issues"] == []
