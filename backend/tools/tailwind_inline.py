"""
Conversion minimale de classes Tailwind → styles inline pour les démos HTML autonomes.
"""

from __future__ import annotations

import re

from tools.demo_preview_html import TAILWIND_PALETTE

_RE_CLASSNAME = re.compile(
    r'className\s*=\s*(?:\{\s*`([^`]+)`\s*\}|"([^"]+)"|\'([^\']+)\')',
    re.I,
)

_SPACING_SCALE: dict[str, str] = {
    f"p-{n}": f"padding:{n * 0.25}rem" for n in range(0, 13)
}
_SPACING_SCALE.update({f"px-{n}": f"padding-left:{n * 0.25}rem;padding-right:{n * 0.25}rem" for n in range(0, 13)})
_SPACING_SCALE.update({f"py-{n}": f"padding-top:{n * 0.25}rem;padding-bottom:{n * 0.25}rem" for n in range(0, 13)})
_SPACING_SCALE.update({f"m-{n}": f"margin:{n * 0.25}rem" for n in range(0, 13)})
_SPACING_SCALE.update({f"mb-{n}": f"margin-bottom:{n * 0.25}rem" for n in range(0, 13)})
_SPACING_SCALE.update({f"mt-{n}": f"margin-top:{n * 0.25}rem" for n in range(0, 13)})
_SPACING_SCALE.update({f"gap-{n}": f"gap:{n * 0.25}rem" for n in range(0, 13)})

_MAX_WIDTH: dict[str, str] = {
    "max-w-sm": "max-width:24rem",
    "max-w-md": "max-width:28rem",
    "max-w-lg": "max-width:32rem",
    "max-w-xl": "max-width:36rem",
    "max-w-2xl": "max-width:42rem",
    "max-w-4xl": "max-width:56rem",
}

_TEXT_SIZE: dict[str, str] = {
    "text-xs": "font-size:0.75rem",
    "text-sm": "font-size:0.875rem",
    "text-base": "font-size:1rem",
    "text-lg": "font-size:1.125rem",
    "text-xl": "font-size:1.25rem",
    "text-2xl": "font-size:1.5rem",
    "text-3xl": "font-size:1.875rem",
}

_ROUNDED: dict[str, str] = {
    "rounded": "border-radius:0.25rem",
    "rounded-md": "border-radius:0.375rem",
    "rounded-lg": "border-radius:0.5rem",
    "rounded-xl": "border-radius:0.75rem",
    "rounded-full": "border-radius:9999px",
}


def extract_class_strings(source: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _RE_CLASSNAME.finditer(source):
        cls = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if cls and cls not in seen:
            seen.add(cls)
            found.append(cls)
    return found


def _color_decl(prefix: str, token: str) -> str | None:
    """bg-slate-900 → background, text-cyan-400 → color, border-slate-700 → border-color."""
    match = re.match(rf"^{prefix}-(.+)$", token)
    if not match:
        return None
    label = match.group(1)
    value = TAILWIND_PALETTE.get(label)
    if not value:
        return None
    css_prop = {
        "bg": "background",
        "text": "color",
        "border": "border-color",
    }.get(prefix, prefix)
    return f"{css_prop}:{value}"


def class_string_to_inline_style(class_str: str) -> str:
    decls: list[str] = []
    seen_props: set[str] = set()

    def add(decl: str) -> None:
        prop = decl.split(":", 1)[0]
        if prop not in seen_props:
            seen_props.add(prop)
            decls.append(decl)

    for raw in class_str.split():
        token = raw.strip()
        if not token or token.startswith("hover:") or token.startswith("focus:"):
            continue
        if token in ("flex", "inline-flex", "grid", "block", "hidden"):
            add(f"display:{token}" if token != "hidden" else "display:none")
            continue
        if token in ("flex-col", "flex-row", "flex-wrap", "items-center", "items-start", "justify-center", "justify-between"):
            mapping = {
                "flex-col": "flex-direction:column",
                "flex-row": "flex-direction:row",
                "flex-wrap": "flex-wrap:wrap",
                "items-center": "align-items:center",
                "items-start": "align-items:flex-start",
                "justify-center": "justify-content:center",
                "justify-between": "justify-content:space-between",
            }
            add(mapping[token])
            continue
        if token == "min-h-screen":
            add("min-height:100vh")
            continue
        if token == "w-full":
            add("width:100%")
            continue
        if token == "mx-auto":
            add("margin-left:auto;margin-right:auto")
            continue
        if token == "line-through":
            add("text-decoration:line-through")
            continue
        if token == "font-bold":
            add("font-weight:700")
            continue
        if token == "font-semibold":
            add("font-weight:600")
            continue
        if token == "font-medium":
            add("font-weight:500")
            continue
        if token == "border":
            add("border-width:1px;border-style:solid")
            continue
        if token == "shadow" or token == "shadow-md" or token == "shadow-lg":
            add("box-shadow:0 4px 14px rgba(0,0,0,0.25)")
            continue
        if token == "opacity-60" or token == "opacity-50":
            add("opacity:0.6")
            continue
        if token in _SPACING_SCALE:
            add(_SPACING_SCALE[token])
            continue
        if token in _MAX_WIDTH:
            add(_MAX_WIDTH[token])
            continue
        if token in _TEXT_SIZE:
            add(_TEXT_SIZE[token])
            continue
        if token in _ROUNDED:
            add(_ROUNDED[token])
            continue
        for prefix in ("bg", "text", "border"):
            decl = _color_decl(prefix, token)
            if decl:
                add(decl)
                break

    return ";".join(decls)


def pick_class(source: str, *needles: str, fallback: str = "") -> str:
    for cls in extract_class_strings(source):
        if any(n in cls for n in needles):
            return cls
    return fallback


def inline_style(source: str, *needles: str, fallback: str = "") -> str:
    cls = pick_class(source, *needles, fallback=fallback)
    if not cls:
        return fallback
    converted = class_string_to_inline_style(cls)
    return converted or fallback
