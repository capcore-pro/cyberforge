"""
Thème CapCore forcé — fond noir #0D0D0D, accents or #C9A84C, sans bleu.
"""

from __future__ import annotations

import re

CAPCORE_BACKGROUND = "#0D0D0D"
CAPCORE_GOLD = "#C9A84C"
CAPCORE_TEXT = "#F5F5F5"

# Hex bleus courants (Tailwind / shadcn / templates premium)
_BLUE_HEX_VALUES: tuple[str, ...] = (
    "#2563eb",
    "#3b82f6",
    "#1d4ed8",
    "#1e40af",
    "#0ea5e9",
    "#0284c7",
    "#0369a1",
    "#6366f1",
    "#4f46e5",
    "#4338ca",
    "#60a5fa",
    "#7c3aed",
    "#8b5cf6",
    "#0891b2",
    "#06b6d4",
    "#22d3ee",
    "#1e3a8a",
    "#172554",
    "#0c1222",
    "#0b0f1a",
)

_CAPCORE_OVERRIDE_CSS = f"""
/* CapCore theme enforced */
:root {{
  --cf-bg: {CAPCORE_BACKGROUND} !important;
  --cf-surface: #141414 !important;
  --cf-primary: {CAPCORE_GOLD} !important;
  --cf-secondary: {CAPCORE_GOLD} !important;
  --cf-accent: {CAPCORE_GOLD} !important;
  --cf-text: {CAPCORE_TEXT} !important;
  --cf-muted: #a3a3a3 !important;
  --cf-glow: rgba(201, 168, 76, 0.35) !important;
  --primary: 43 52% 58% !important;
  --secondary: 43 52% 58% !important;
  --accent: 43 52% 58% !important;
  --ring: 43 52% 58% !important;
  --background: 0 0% 5% !important;
}}
html, body {{
  background: {CAPCORE_BACKGROUND} !important;
  background-color: {CAPCORE_BACKGROUND} !important;
  color: {CAPCORE_TEXT} !important;
}}
"""

_BLUE_WORD_RE = re.compile(
    r"\b(?:blue|indigo|sky|cyan)(?:-\d{{2,3}})?\b",
    re.IGNORECASE,
)


def _replace_blue_hex(content: str) -> str:
    out = content
    for blue in _BLUE_HEX_VALUES:
        if blue.lower() in ("#0c1222", "#0b0f1a", "#172554", "#1e3a8a"):
            out = re.sub(re.escape(blue), CAPCORE_BACKGROUND, out, flags=re.IGNORECASE)
        else:
            out = re.sub(re.escape(blue), CAPCORE_GOLD, out, flags=re.IGNORECASE)
    return out


def _replace_blue_tailwind_tokens(content: str) -> str:
    return _BLUE_WORD_RE.sub(CAPCORE_GOLD.replace("#", ""), content)


def _inject_capcore_css_block(html: str) -> str:
    if "CapCore theme enforced" in html:
        return html
    lower = html.lower()
    style_idx = lower.find("<style")
    if style_idx >= 0:
        close = html.find(">", style_idx)
        if close >= 0:
            return html[: close + 1] + _CAPCORE_OVERRIDE_CSS + html[close + 1 :]
    if "</head>" in lower:
        block = f"<style>{_CAPCORE_OVERRIDE_CSS}</style>\n"
        return re.sub(r"</head>", block + "</head>", html, count=1, flags=re.IGNORECASE)
    return f"<style>{_CAPCORE_OVERRIDE_CSS}</style>\n" + html


def enforce_capcore_theme(content: str) -> str:
    """
    Force le thème noir/or et retire les teintes bleues d'un fichier HTML ou CSS.
    """
    if not content or not content.strip():
        return content
    patched = _replace_blue_hex(content)
    patched = _replace_blue_tailwind_tokens(patched)
    if "<html" in patched.lower() or "<!doctype" in patched.lower():
        patched = _inject_capcore_css_block(patched)
    elif "{" in patched and ("--cf-" in patched or "color:" in patched or "background" in patched):
        if "CapCore theme enforced" not in patched:
            patched = _CAPCORE_OVERRIDE_CSS.strip() + "\n" + patched
    return patched


def enforce_capcore_theme_on_files(files: dict[str, str]) -> dict[str, str]:
    """Applique le thème CapCore à tous les fichiers CSS/HTML/Tailwind."""
    out: dict[str, str] = {}
    for path, body in files.items():
        lower = path.lower()
        if lower.endswith((".html", ".css", ".tsx", ".jsx", ".ts", ".js")) or "tailwind" in lower:
            out[path] = enforce_capcore_theme(body)
        else:
            out[path] = body
    return out
