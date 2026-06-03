"""Tests post-traitement HTML vitrine."""

import pytest

from tools.vitrine_html_enhance import (
    enhance_builder_vitrine_html,
    find_forbidden_placeholder_issues,
)


@pytest.mark.skip(reason="DÉSACTIVÉ TEMPORAIREMENT - DEBUG — find_forbidden_placeholder")
def test_forbidden_lorem_detected() -> None:
    issues = find_forbidden_placeholder_issues("<p>Lorem ipsum dolor</p>")
    assert any(code == "generic_placeholder" for code, _ in issues)


def test_fix_dead_href_and_contact_injection() -> None:
    html = "<!DOCTYPE html><html><body><a href='#'>CTA</a></body></html>"
    out = enhance_builder_vitrine_html(html, client_name="Test Co")
    assert 'data-cf-action="scroll"' in out
    assert "cf-contact-form" in out
    assert "submitDemoContact" in out
