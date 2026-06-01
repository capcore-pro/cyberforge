"""
Nettoyage des fences markdown dans le HTML livré (sorties LLM ou copier-coller).
"""

from __future__ import annotations

import re

_FENCE_OPEN_RE = re.compile(
    r"^[\s\uFEFF]*```(?:html|htm|xml|markdown|md)?\s*\r?\n?",
    re.IGNORECASE | re.MULTILINE,
)
_FENCE_CLOSE_RE = re.compile(r"\r?\n?```[\s\uFEFF]*(?:\r?\n|$)", re.MULTILINE)
_STRAY_FENCE_RE = re.compile(r"```(?:html|htm)?", re.IGNORECASE)


def strip_markdown_code_fences(html: str) -> str:
    """Retire ```html, ``` et fences orphelins du document."""
    if not html or not html.strip():
        return html
    out = html.replace("\ufeff", "")
    for _ in range(8):
        prev = out
        out = _FENCE_OPEN_RE.sub("", out, count=1)
        out = _FENCE_CLOSE_RE.sub("\n", out, count=1)
        out = _STRAY_FENCE_RE.sub("", out)
        if out == prev:
            break
    return out.strip()
