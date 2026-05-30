"""Annotation automatique data-cms sur le code HTML/JSX généré par BuilderAI."""

from __future__ import annotations

import re
from collections import defaultdict

_MARKUP_EXTENSIONS = (".html", ".htm", ".tsx", ".jsx")
_CSS_EXTENSIONS = (".css",)
_SKIP_ATTR_FRAGMENTS = (
    "data-cms=",
    "sr-only",
    "aria-hidden",
    "type=\"hidden\"",
    "type='hidden'",
)

_TEXT_TAG_RE = re.compile(
    r"<(h1|h2|h3|p|button|a)\b([^>]*?)(/?)>",
    re.IGNORECASE,
)
_IMG_TAG_RE = re.compile(r"<img\b([^>]*?)(/?)>", re.IGNORECASE)
_BG_DIV_RE = re.compile(
    r"<div\b([^>]*?style\s*=\s*[\"'][^\"']*background-image[^\"']*[\"'][^>]*?)(/?)>",
    re.IGNORECASE,
)
_STYLE_COLOR_RE = re.compile(
    r"<([a-zA-Z][\w.-]*)\b([^>]*?style\s*=\s*[\"'][^\"']*(?:--primary|--secondary|--accent|--cf-primary|--cf-secondary|--cf-accent)[^\"']*[\"'][^>]*?)(/?)>",
    re.IGNORECASE,
)
_ROOT_BLOCK_RE = re.compile(r"(:root\s*\{)", re.IGNORECASE)


def _should_skip_attrs(attrs: str) -> bool:
    lower = attrs.lower()
    return any(fragment in lower for fragment in _SKIP_ATTR_FRAGMENTS)


def _slugify(text: str, max_len: int = 32) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", text.strip().lower()).strip(".")
    return (cleaned or "block")[:max_len]


def _next_key(counters: dict[str, int], kind: str, hint: str) -> str:
    counters[kind] += 1
    slug = _slugify(hint) if hint else kind
    return f"cms.auto.{kind}.{slug}.{counters[kind]}"


def annotate_markup_content(content: str, *, file_hint: str = "page") -> str:
    """Ajoute data-cms sur textes, images et couleurs inline."""
    if not content.strip():
        return content

    counters: dict[str, int] = defaultdict(int)
    prefix = _slugify(file_hint.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0])

    def _text_repl(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        attrs = match.group(2) or ""
        closing = match.group(3) or ""
        if _should_skip_attrs(attrs):
            return match.group(0)
        key = _next_key(counters, "text", f"{prefix}.{tag}")
        return f'<{tag} data-cms="text" data-cms-key="{key}"{attrs}{closing}>'

    def _img_repl(match: re.Match[str]) -> str:
        attrs = match.group(1) or ""
        closing = match.group(2) or ""
        if _should_skip_attrs(attrs):
            return match.group(0)
        key = _next_key(counters, "image", f"{prefix}.img")
        return f'<img data-cms="image" data-cms-key="{key}"{attrs}{closing}>'

    def _bg_div_repl(match: re.Match[str]) -> str:
        attrs = match.group(1) or ""
        closing = match.group(2) or ""
        if _should_skip_attrs(attrs):
            return match.group(0)
        key = _next_key(counters, "image", f"{prefix}.bg")
        return f'<div data-cms="image" data-cms-key="{key}" {attrs}{closing}>'

    def _color_repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs = match.group(2) or ""
        closing = match.group(3) or ""
        if _should_skip_attrs(attrs):
            return match.group(0)
        key = _next_key(counters, "color", f"{prefix}.{tag.lower()}")
        return f'<{tag} data-cms="color" data-cms-key="{key}"{attrs}{closing}>'

    updated = _TEXT_TAG_RE.sub(_text_repl, content)
    updated = _IMG_TAG_RE.sub(_img_repl, updated)
    updated = _BG_DIV_RE.sub(_bg_div_repl, updated)
    updated = _STYLE_COLOR_RE.sub(_color_repl, updated)
    return updated


def annotate_css_content(content: str, *, file_hint: str = "theme") -> str:
    """Marque le bloc :root pour les couleurs CMS."""
    if ":root" not in content or "data-cms" in content:
        return content
    prefix = _slugify(file_hint)
    marker = (
        f"\n  /* cms-color-block {prefix} */\n"
        f'  --cms-marked: "color";\n'
    )

    def _root_repl(match: re.Match[str]) -> str:
        return match.group(1) + marker

    return _ROOT_BLOCK_RE.sub(_root_repl, content, count=1)


def annotate_file_content(path: str, content: str) -> str:
    lower = path.lower()
    if lower.endswith(_MARKUP_EXTENSIONS):
        return annotate_markup_content(content, file_hint=path)
    if lower.endswith(_CSS_EXTENSIONS):
        return annotate_css_content(content, file_hint=path)
    return content
