"""Tests bypass aperçu interne CyberForge."""

from tools.demo_preview_gate import (
    append_cyberforge_internal_preview_query,
    prepare_internal_app_preview_html,
    strip_password_gate,
)
from tools.standalone_demo_html import wrap_with_password_gate


def test_append_internal_preview_query() -> None:
    url = append_cyberforge_internal_preview_query("https://demo.pages.dev/site")
    assert "preview=cyberforge_internal" in url


def test_strip_gate_for_internal_preview() -> None:
    inner = "<h1>Client</h1><section id='contact'><form></form></section>"
    gated = wrap_with_password_gate(inner, "secret-pass", title="Test")
    assert "cf-login-screen" in gated
    stripped = prepare_internal_app_preview_html(gated)
    assert "Démo protégée" not in stripped
    assert "Client" in stripped
