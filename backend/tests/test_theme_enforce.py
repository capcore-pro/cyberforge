"""Tests thème CapCore — noir/or, sans bleu."""

from tools.theme_enforce import CAPCORE_BACKGROUND, CAPCORE_GOLD, enforce_capcore_theme


def test_replaces_blue_hex_with_gold() -> None:
    html = "<style>.btn { color: #2563eb; background: #3b82f6; }</style>"
    out = enforce_capcore_theme(html)
    assert "#2563eb" not in out.lower()
    assert "#3b82f6" not in out.lower()
    assert CAPCORE_GOLD in out


def test_injects_capcore_root_variables() -> None:
    html = "<!DOCTYPE html><html><head></head><body><p>Hi</p></body></html>"
    out = enforce_capcore_theme(html)
    assert CAPCORE_BACKGROUND in out
    assert "CapCore theme enforced" in out
