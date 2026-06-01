"""Tests nettoyage fences markdown dans le HTML."""

from __future__ import annotations

from tools.html_markdown import strip_markdown_code_fences


def test_strip_html_fence_at_start() -> None:
    raw = "```html\n<!DOCTYPE html><html><body><h1>Test</h1></body></html>\n```"
    out = strip_markdown_code_fences(raw)
    assert "```" not in out
    assert out.startswith("<!DOCTYPE html>")


def test_strip_stray_fence_tokens() -> None:
    out = strip_markdown_code_fences("```html visible\n<h1>Hi</h1>")
    assert "visible" in out
    assert "```html" not in out
