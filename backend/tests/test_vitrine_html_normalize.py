"""Tests normalisation HTML vitrine."""

from __future__ import annotations

from tools.vitrine_html_normalize import (
    extract_unlocked_demo_html,
    normalize_vitrine_html_document,
)


def test_normalize_minimal_fragment() -> None:
    html = "<div><p>Hello</p></div>"
    out = normalize_vitrine_html_document(html, page_title="Test Co", client_name="Test Co")
    assert "<!DOCTYPE html>" in out
    assert '<meta charset="UTF-8"' in out
    assert "<h1>" in out
    assert 'id="contact"' in out
    assert "cf-contact-form" in out


def test_extract_unlocked_demo_strips_login() -> None:
    wrapped = """<!DOCTYPE html><html><head><title>T</title></head><body>
    <div id="cf-login-screen"><h1>Login</h1></div>
    <div id="cf-demo-content"><section id="hero"><h1>Client</h1></section>
    <section id="contact"><form id="cf-contact-form"></form></section></div>
    </body></html>"""
    out = extract_unlocked_demo_html(wrapped)
    assert "cf-playwright-unlock" in out or "<h1>Client</h1>" in out
    assert "<h1>Client</h1>" in out


def test_normalize_adds_charset() -> None:
    raw = "<html><head><title>Dupont</title></head><body><h1>Dupont</h1></body></html>"
    out = normalize_vitrine_html_document(raw, client_name="Dupont")
    assert "UTF-8" in out
    assert "Dupont" in out
