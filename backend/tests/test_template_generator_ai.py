"""Tests TemplateGeneratorAI — validation HTML et routage pipeline."""

from __future__ import annotations

from agents.template_generator_ai import (
    MAX_HTML_CHARS,
    TemplateGeneratorResult,
    _extract_html_from_response,
    _validate_generated_html,
)
from agents.pipeline_graph import (
    GENERATED_TEMPLATE_PRICING_CATEGORIES,
    _should_use_template_generator,
)


def test_validate_generated_html_accepts_minimal_document() -> None:
    html = """<!DOCTYPE html>
<html lang="fr"><head><title>T</title><style>:root{--color-primary:#111;--color-secondary:#fff}</style></head>
<body><header><nav><a href="#top">X</a></nav></header>
<section class="hero"><h1>{{CLIENT_NAME}}</h1><p>{{CLIENT_TAGLINE}}</p>
<img class="cf-image" src="{{HERO_IMAGE}}" alt="hero" /></section>
<section><h2>{{SECTION_1_TITLE}}</h2><p>{{SECTION_1_CONTENT}}</p></section>
<section><h2>{{SECTION_2_TITLE}}</h2><p>{{SECTION_2_CONTENT}}</p></section>
<section><h2>{{SECTION_3_TITLE}}</h2><p>{{SECTION_3_CONTENT}}</p></section>
<footer>f</footer></body></html>"""
    assert _validate_generated_html(html) is None


def test_validate_rejects_html_over_max_chars() -> None:
    base = (
        "<!DOCTYPE html><html><body><header><nav></nav></header>"
        '<section class="hero"><h1>{{CLIENT_NAME}}</h1><p>{{CLIENT_TAGLINE}}</p></section>'
        "<section><h2>{{SECTION_1_TITLE}}</h2><p>{{SECTION_1_CONTENT}}</p></section>"
        "<section><h2>{{SECTION_2_TITLE}}</h2><p>{{SECTION_2_CONTENT}}</p></section>"
        "<section><h2>{{SECTION_3_TITLE}}</h2><p>{{SECTION_3_CONTENT}}</p></section>"
        "<footer></footer></body></html>"
    )
    html = base + (" " * (MAX_HTML_CHARS - len(base) + 1))
    err = _validate_generated_html(html)
    assert err is not None
    assert "trop long" in err


def test_extract_html_strips_markdown_fence() -> None:
    raw = "```html\n<!DOCTYPE html><html><body><header></header>"
    "section class=\"hero\">{{CLIENT_NAME}}</section>"
    "<section><h2>{{SECTION_1_TITLE}}</h2></section></body></html>\n```"
    out = _extract_html_from_response(raw)
    assert "<html" in out.lower()


def test_pricing_categories_for_generator() -> None:
    assert "vitrine_next" in GENERATED_TEMPLATE_PRICING_CATEGORIES
    assert "ecommerce" in GENERATED_TEMPLATE_PRICING_CATEGORIES
    assert "site_reservation" in GENERATED_TEMPLATE_PRICING_CATEGORIES


def test_should_use_template_generator() -> None:
    from agents.architect_agent import ArchitectPlan, ToolboxPalette
    from agents.coremind_agent import ProjectType

    plan = ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site",
        template="landing",
        template_label="Landing",
        rationale="",
        complexity_score=3,
        complexity_label="Moyenne",
        market_price_min=500,
        market_price_max=2000,
        suggested_price_min=200,
        suggested_price_max=800,
        palette=ToolboxPalette(primary="#2563EB", secondary="#F8FAFC", accent="#F59E0B"),
        pricing_category="vitrine_next",
    )
    state = {"architect_plan": plan}
    assert _should_use_template_generator(state) is True
