"""Tests Firecrawl — parsing de réponse et helpers."""

from tools.firecrawl_client import (
    FirecrawlError,
    _extract_couleurs,
    _parse_firecrawl_payload,
)


def test_parse_firecrawl_payload_minimal() -> None:
    payload = {
        "success": True,
        "data": {
            "metadata": {
                "title": "Acme Restaurant",
                "description": "Fine dining in Paris",
            },
            "markdown": "# Welcome\n\n## Our services\n\nGreat food.",
            "html": (
                '<html><body><h1>Welcome</h1>'
                '<img src="/hero.jpg" alt="hero" />'
                '<a href="/book">Réserver une table</a></body></html>'
            ),
            "json": {
                "titres": ["Welcome", "Our services"],
                "descriptions": ["Great food."],
                "cta_texts": ["Réserver une table"],
                "temoignages": ["Excellent!"],
                "sections": [
                    {"type": "hero", "heading": "Welcome", "summary": "Intro"},
                    {"type": "services", "heading": "Our services"},
                ],
            },
            "branding": {
                "colors": {
                    "primary": "#8B2E1F",
                    "secondary": "#F5E6D3",
                    "accent": "#D4A853",
                }
            },
            "images": ["https://cdn.example/hero.jpg"],
        },
    }
    result = _parse_firecrawl_payload("https://example.com", payload)
    assert result.title == "Acme Restaurant"
    assert result.meta_description == "Fine dining in Paris"
    assert len(result.sections) >= 2
    assert result.sections[0].type == "hero"
    assert "Réserver une table" in result.cta_texts
    assert result.couleurs.get("primary") == "#8B2E1F"
    assert any("hero.jpg" in img.url for img in result.images)


def test_parse_firecrawl_failure() -> None:
    try:
        _parse_firecrawl_payload("https://x.com", {"success": False, "error": "fail"})
        raised = False
    except FirecrawlError:
        raised = True
    assert raised


def test_extract_couleurs_from_html_fallback() -> None:
    colors = _extract_couleurs(None, '<div style="color:#112233">x</div>')
    assert colors.get("primary") == "#112233"
