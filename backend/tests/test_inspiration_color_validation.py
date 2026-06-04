"""Validation couleurs clone inspiration — luminosité."""

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("anthropic", MagicMock())

from tools.inspiration_analysis import (  # noqa: E402
    CAMPING_PRIMARY_FALLBACK,
    is_color_too_light,
    validate_brand_hex,
)


def test_light_color_rejected_for_camping() -> None:
    assert is_color_too_light("#f5f5f5") is True
    assert validate_brand_hex("#f5f5f5", secteur="camping plein air") == CAMPING_PRIMARY_FALLBACK


def test_dark_color_kept() -> None:
    assert validate_brand_hex("#2d6a4f", secteur="camping") == "#2d6a4f"
