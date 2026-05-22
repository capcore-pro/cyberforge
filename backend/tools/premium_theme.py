"""Couleur principale et thème CSS pour templates premium."""

from __future__ import annotations

import re

_DEFAULT_PRIMARY = "#6366f1"


def sanitize_primary_color(value: str | None, *, default: str = _DEFAULT_PRIMARY) -> str:
    if not value or not str(value).strip():
        return default
    raw = str(value).strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw):
        return raw.lower()
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", raw):
        h = raw[1:]
        return "#" + "".join(ch * 2 for ch in h).lower()
    if re.fullmatch(r"[0-9A-Fa-f]{6}", raw):
        return f"#{raw.lower()}"
    return default


def build_primary_theme_css(primary_color: str | None) -> str:
    """Surcharges accent (boutons, nav active, logo sans image uploadée)."""
    return build_theme_css(primary_color, None)


def build_theme_css(
    primary_color: str | None,
    secondary_color: str | None = None,
) -> str:
    """Couleur principale + secondaire pour dégradés et accents."""
    primary = sanitize_primary_color(primary_color)
    secondary = sanitize_primary_color(secondary_color, default="#22d3ee")
    return f"""
    :root {{ --cf-primary: {primary}; --cf-secondary: {secondary}; }}
    .saas-logo:not(.saas-logo-img) {{
      background: linear-gradient(135deg, {primary}, {secondary}) !important;
      box-shadow: 0 6px 20px color-mix(in srgb, {primary} 38%, transparent) !important;
    }}
    .saas-nav-item.active {{
      background: color-mix(in srgb, {primary} 22%, transparent) !important;
      border-color: color-mix(in srgb, {primary} 32%, transparent) !important;
    }}
    .saas-nav-dot {{ background: {primary} !important; }}
    .saas-menu-btn:hover {{
      background: color-mix(in srgb, {primary} 18%, transparent) !important;
      border-color: color-mix(in srgb, {primary} 28%, transparent) !important;
    }}
    .btn-add {{
      background: linear-gradient(135deg, {primary}, color-mix(in srgb, {primary} 70%, #312e81)) !important;
    }}
    .progress-fill {{ background: linear-gradient(90deg, {primary}, {secondary}) !important; }}
    .team-avatar, .saas-user-avatar {{
      background: linear-gradient(135deg, {primary}, {secondary}) !important;
    }}
    .cf-btn-primary, .cf-btn.cf-btn-primary {{
      background: linear-gradient(135deg, {primary}, color-mix(in srgb, {primary} 75%, #312e81)) !important;
      box-shadow: 0 4px 18px color-mix(in srgb, {primary} 42%, transparent) !important;
    }}
    """
