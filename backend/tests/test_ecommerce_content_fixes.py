"""E-commerce — rayons, images produits, navigation démo."""

from __future__ import annotations

import asyncio

from agents.content_ai import build_content_slots, fill_template_content
from agents.template_ai import load_sector_template_html
from core.agent_contract import require_ok
from tools.ecommerce_product_images import ensure_ecommerce_product_thumbnails
from tools.standalone_demo_html import inject_demo_link_navigation_script


def test_ecommerce_alimentaire_categories_never_saas_keywords() -> None:
    slots = build_content_slots(
        client_name="Test",
        sector="saas",
        city="Rouen",
        template_html=load_sector_template_html("ecommerce_alimentaire.html"),
        research_content={"mots_cles": ["solutions", "saas", "dashboard"]},
        template_id="ecommerce_alimentaire",
        user_prompt="boutique solutions saas Rouen",
    )
    for key in ("CATEGORY_1", "CATEGORY_2", "CATEGORY_3"):
        low = slots[key].lower()
        assert "saas" not in low
        assert "solution" not in low
    assert "pains" in slots["CATEGORY_1"].lower() or "artisanaux" in slots["CATEGORY_1"].lower()
    assert "viennoiserie" in slots["CATEGORY_2"].lower()


def test_product_thumbnails_injected() -> None:
    html = """
    <article class="product-card"><div class="thumb"></div></article>
    <article class="product-card"><div class="thumb"></div></article>
    """
    out = ensure_ecommerce_product_thumbnails(html, "ecommerce_alimentaire")
    assert out.count("<img") >= 2
    assert "unsplash.com" in out


def test_fill_ecommerce_includes_images_and_link_script() -> None:
    result = asyncio.run(
        fill_template_content(
            template_html=load_sector_template_html("ecommerce_alimentaire.html"),
            client_name="Le Fournil",
            sector="boulangerie",
            city="Rouen",
            template_id="ecommerce_alimentaire",
            user_prompt="pâtisserie Rouen",
        )
    )
    data = require_ok(result)
    assert "product-card" in data.html
    assert 'class="thumb"' in data.html
    assert "<img" in data.html
    assert 'id="cf-demo-link-nav"' in data.html


def test_inject_link_script_idempotent() -> None:
    html = "<!DOCTYPE html><html><body><a href=\"#contact\">x</a></body></html>"
    once = inject_demo_link_navigation_script(html)
    twice = inject_demo_link_navigation_script(once)
    assert once.count("cf-demo-link-nav") == 1
    assert twice.count("cf-demo-link-nav") == 1
