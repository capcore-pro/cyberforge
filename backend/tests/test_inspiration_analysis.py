"""Tests helpers inspiration — couleurs CSS dominantes."""

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("anthropic", MagicMock())

from tools.inspiration_analysis import dominant_hex_colors_from_html  # noqa: E402


def test_dominant_hex_from_style_blocks() -> None:
    html = """
    <style>
      .hero { color: #1a2b3c; background: #ff5500; }
      .btn { background: #ff5500; border: 1px solid #1a2b3c; }
    </style>
    <p style="color:#ffffff">x</p>
    """
    colors = dominant_hex_colors_from_html(html, limit=3)
    assert colors[0] == "#ff5500"
    assert "#1a2b3c" in colors
