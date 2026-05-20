"""
Conversion TSX/JSX → page HTML statique navigable (sans React ni réseau).
"""

from __future__ import annotations

import re

from tools.demo_preview_html import TAILWIND_PALETTE, escape_attr, escape_html

# Utilitaires Tailwind fréquents (hors palette couleur)
LAYOUT_CSS: dict[str, str] = {
    "min-h-screen": "min-height:100vh",
    "h-full": "height:100%",
    "w-full": "width:100%",
    "flex": "display:flex",
    "grid": "display:grid",
    "grid-cols-1": "grid-template-columns:repeat(1,minmax(0,1fr))",
    "grid-cols-2": "grid-template-columns:repeat(2,minmax(0,1fr))",
    "grid-cols-3": "grid-template-columns:repeat(3,minmax(0,1fr))",
    "hidden": "display:none",
    "block": "display:block",
    "inline-block": "display:inline-block",
    "inline-flex": "display:inline-flex",
    "flex-col": "flex-direction:column",
    "flex-wrap": "flex-wrap:wrap",
    "items-center": "align-items:center",
    "items-start": "align-items:flex-start",
    "items-end": "align-items:flex-end",
    "justify-center": "justify-content:center",
    "justify-between": "justify-content:space-between",
    "justify-start": "justify-content:flex-start",
    "gap-1": "gap:0.25rem",
    "gap-2": "gap:0.5rem",
    "gap-3": "gap:0.75rem",
    "gap-4": "gap:1rem",
    "gap-6": "gap:1.5rem",
    "gap-8": "gap:2rem",
    "mx-auto": "margin-left:auto;margin-right:auto",
    "text-center": "text-align:center",
    "text-left": "text-align:left",
    "text-right": "text-align:right",
    "font-bold": "font-weight:700",
    "font-semibold": "font-weight:600",
    "font-medium": "font-weight:500",
    "uppercase": "text-transform:uppercase",
    "tracking-wide": "letter-spacing:0.025em",
    "tracking-wider": "letter-spacing:0.05em",
    "rounded": "border-radius:0.25rem",
    "rounded-lg": "border-radius:0.5rem",
    "rounded-xl": "border-radius:0.75rem",
    "rounded-full": "border-radius:9999px",
    "shadow": "box-shadow:0 1px 3px rgba(0,0,0,.4)",
    "shadow-md": "box-shadow:0 4px 12px rgba(0,0,0,.25)",
    "shadow-lg": "box-shadow:0 10px 25px rgba(0,0,0,.45)",
    "border": "border-width:1px;border-style:solid",
    "overflow-hidden": "overflow:hidden",
    "overflow-auto": "overflow:auto",
    "relative": "position:relative",
    "absolute": "position:absolute",
    "fixed": "position:fixed",
    "inset-0": "inset:0",
    "bg-cover": "background-size:cover",
    "bg-center": "background-position:center",
    "p-2": "padding:0.5rem",
    "p-4": "padding:1rem",
    "p-6": "padding:1.5rem",
    "p-8": "padding:2rem",
    "px-4": "padding-left:1rem;padding-right:1rem",
    "px-6": "padding-left:1.5rem;padding-right:1.5rem",
    "px-8": "padding-left:2rem;padding-right:2rem",
    "py-2": "padding-top:0.5rem;padding-bottom:0.5rem",
    "py-4": "padding-top:1rem;padding-bottom:1rem",
    "py-6": "padding-top:1.5rem;padding-bottom:1.5rem",
    "py-8": "padding-top:2rem;padding-bottom:2rem",
    "py-12": "padding-top:3rem;padding-bottom:3rem",
    "py-16": "padding-top:4rem;padding-bottom:4rem",
    "py-20": "padding-top:5rem;padding-bottom:5rem",
    "mt-2": "margin-top:0.5rem",
    "mt-4": "margin-top:1rem",
    "mt-6": "margin-top:1.5rem",
    "mt-8": "margin-top:2rem",
    "mb-2": "margin-bottom:0.5rem",
    "mb-4": "margin-bottom:1rem",
    "mb-6": "margin-bottom:1.5rem",
    "mb-8": "margin-bottom:2rem",
    "mb-12": "margin-bottom:3rem",
    "max-w-xl": "max-width:36rem",
    "max-w-3xl": "max-width:48rem",
    "max-w-4xl": "max-width:56rem",
    "max-w-5xl": "max-width:64rem",
    "max-w-6xl": "max-width:72rem",
    "max-w-7xl": "max-width:80rem",
    "space-y-2": "display:flex;flex-direction:column;gap:0.5rem",
    "space-y-4": "display:flex;flex-direction:column;gap:1rem",
    "space-y-6": "display:flex;flex-direction:column;gap:1.5rem",
    "text-xs": "font-size:0.75rem",
    "text-sm": "font-size:0.875rem",
    "text-base": "font-size:1rem",
    "text-lg": "font-size:1.125rem",
    "text-xl": "font-size:1.25rem",
    "text-2xl": "font-size:1.5rem",
    "text-3xl": "font-size:1.875rem",
    "text-4xl": "font-size:2.25rem",
    "text-5xl": "font-size:3rem",
    "leading-relaxed": "line-height:1.625",
    "transition": "transition:all .2s ease",
    "cursor-pointer": "cursor:pointer",
    "object-cover": "object-fit:cover",
    "z-10": "z-index:10",
    "hover:shadow-lg": "transition:box-shadow .2s ease",
}

RESPONSIVE_CSS: dict[str, str] = {
    "md:grid-cols-2": "grid-template-columns:repeat(2,minmax(0,1fr))",
    "md:grid-cols-3": "grid-template-columns:repeat(3,minmax(0,1fr))",
    "md:text-2xl": "font-size:1.5rem",
    "md:text-7xl": "font-size:4.5rem",
}

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

_JSX_ARTIFACT_RE = re.compile(
    r"\}\}\}?|\.map\s*\(|=>\s*\(?|\(\s*\w+\s*\)\s*=>|key=\{[^}]*\}",
    re.I,
)


def _strip_source(source: str) -> str:
    code = re.sub(r"/\*[\s\S]*?\*/", "", source)
    code = re.sub(r"//.*$", "", code, flags=re.M)
    code = re.sub(r"^import\s.+$", "", code, flags=re.M)
    code = re.sub(r"^export\s+default\s+", "", code, flags=re.M)
    return code


def _extract_return_jsx(source: str) -> str:
    code = _strip_source(source)
    match = re.search(r"return\s*\(", code)
    if not match:
        return code.strip()
    start = match.end()
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        ch = code[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    return code[start : i - 1].strip()


def _scan_bracket_block(text: str, open_ch: str, close_ch: str, start: int) -> int | None:
    """Retourne l'index après le close_ch correspondant, ou None."""
    if start >= len(text) or text[start] != open_ch:
        return None
    depth = 0
    i = start
    in_string: str | None = None
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            i += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _parse_object_literal(body: str) -> dict[str, str]:
    """Parse un littéral objet JS simple { key: 'value', ... }."""
    fields: dict[str, str] = {}
    inner = body.strip()
    if not inner.startswith("{") or not inner.endswith("}"):
        return fields
    inner = inner[1:-1]
    for part in re.split(r",(?=(?:[^'\"`]*['\"`][^'\"`]*['\"`])*[^'\"`]*$)", inner):
        piece = part.strip()
        if not piece or ":" not in piece:
            continue
        key, _, val = piece.partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip().strip(",").strip()
        if (val.startswith("'") and val.endswith("'")) or (
            val.startswith('"') and val.endswith('"')
        ):
            val = val[1:-1]
        fields[key] = val
    return fields


def _parse_array_of_objects(array_inner: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    i = 0
    while i < len(array_inner):
        if array_inner[i] != "{":
            i += 1
            continue
        end = _scan_bracket_block(array_inner, "{", "}", i)
        if end is None:
            break
        obj = _parse_object_literal(array_inner[i:end])
        if obj:
            items.append(obj)
        i = end
    return items


def _substitute_item_fields(template: str, var_name: str, fields: dict[str, str]) -> str:
    out = template
    for key, value in fields.items():
        safe = escape_html(value)
        out = out.replace(f"{{{var_name}.{key}}}", safe)
        out = out.replace(f"{{ {var_name}.{key} }}", safe)
        out = re.sub(
            rf"\b{re.escape(var_name)}\.{re.escape(key)}\b",
            safe,
            out,
        )
    out = re.sub(rf'\s*key=\{{?\s*{re.escape(var_name)}\.\w+\s*\}}?', "", out)
    out = re.sub(rf'\s*key="{re.escape(var_name)}\.[^"]*"', "", out)
    return out


def _expand_map_calls(text: str) -> str:
    """Déplie {[...].map((item) => (...))} en HTML statique répété."""
    while True:
        match = re.search(r"\.map\s*\(\s*\(\s*(\w+)\s*\)\s*=>\s*\(", text)
        if not match:
            break

        var_name = match.group(1)
        map_pos = match.start()
        close_bracket = text.rfind("]", 0, map_pos)
        if close_bracket < 0:
            break
        open_bracket = text.rfind("[", 0, close_bracket)
        if open_bracket < 0:
            break

        expr_start = text.rfind("{", 0, open_bracket)
        if expr_start < 0:
            expr_start = open_bracket

        array_inner = text[open_bracket + 1 : close_bracket]
        items = _parse_array_of_objects(array_inner)
        if not items:
            break

        template_start = match.end()
        template_end = _scan_bracket_block(text, "(", ")", template_start - 1)
        if template_end is None:
            break
        template = text[template_start:template_end - 1]

        expanded = "".join(
            _substitute_item_fields(template, var_name, item) for item in items
        )

        expr_close = template_end
        while expr_close < len(text) and text[expr_close] in " \t\n\r":
            expr_close += 1
        if expr_close < len(text) and text[expr_close] == ")":
            expr_close += 1
        while expr_close < len(text) and text[expr_close] in " \t\n\r":
            expr_close += 1
        if expr_close < len(text) and text[expr_close] == "}":
            expr_close += 1

        text = text[:expr_start] + expanded + text[expr_close:]

    return text


def _convert_style_objects(text: str) -> str:
    """style={{ backgroundImage: \"url(...)\" }} → style=\"background-image: url(...)\"."""

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        pairs: list[str] = []
        for part in re.split(r",(?=(?:[^'\"]*['\"][^'\"]*)*[^'\"]*$)", inner):
            piece = part.strip()
            if not piece or ":" not in piece:
                continue
            key, _, val = piece.partition(":")
            key = key.strip().strip('"').strip("'")
            camel = re.sub(r"([A-Z])", r"-\1", key).lower()
            val = val.strip().rstrip(",").strip()
            if (val.startswith("'") and val.endswith("'")) or (
                val.startswith('"') and val.endswith('"')
            ):
                val = val[1:-1]
            pairs.append(f"{camel}:{val}")
        if not pairs:
            return ""
        return f' style="{";".join(pairs)}"'

    return re.sub(
        r"style=\{\{([\s\S]*?)\}\}\}",
        repl,
        text,
    )


def _remove_jsx_expressions(text: str) -> str:
    """Supprime les expressions {…} avec accolades imbriquées."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] != "{":
            out.append(text[i])
            i += 1
            continue
        end = _scan_bracket_block(text, "{", "}", i)
        if end is None:
            out.append(text[i])
            i += 1
            continue
        i = end
    return "".join(out)


def _cleanup_jsx_artifacts(text: str) -> str:
    text = _JSX_ARTIFACT_RE.sub("", text)
    text = re.sub(r"\{+\s*\}+", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r">\s+<", "><", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _jsx_to_html(jsx: str) -> str:
    html = jsx
    html = re.sub(r"\{/\*[\s\S]*?\*/\}", "", html)
    html = _convert_style_objects(html)
    html = _expand_map_calls(html)
    html = _remove_jsx_expressions(html)
    html = re.sub(r"className\s*=", "class=", html)
    html = re.sub(r"htmlFor\s*=", "for=", html)
    html = re.sub(r"\{`([^`]*)`\}", r"\1", html)
    html = _cleanup_jsx_artifacts(html)
    html = re.sub(r"\s+/", " /", html)

    def close_void_tags(text: str) -> str:
        for tag in VOID_TAGS:
            text = re.sub(
                rf"<{tag}(\s[^>/]*)>(?!</{tag}>)",
                rf"<{tag}\1 />",
                text,
                flags=re.I,
            )
            text = re.sub(rf"<{tag}\s*/>\s*</{tag}>", rf"<{tag} />", text, flags=re.I)
        return text

    html = close_void_tags(html)

    html = re.sub(
        r"<([A-Z][A-Za-z0-9]*)([^>]*)>",
        lambda m: f'<div data-component="{escape_attr(m.group(1))}"{m.group(2)}>',
        html,
    )
    html = re.sub(r"</[A-Z][A-Za-z0-9]*>", "</div>", html)
    return html.strip()


def _collect_classes(html: str) -> set[str]:
    classes: set[str] = set()
    for match in re.finditer(r'class="([^"]*)"', html):
        for token in match.group(1).split():
            classes.add(token.strip())
    return classes


def _css_for_class(token: str) -> str | None:
    if token in LAYOUT_CSS:
        return LAYOUT_CSS[token]
    color = TAILWIND_PALETTE.get(token)
    if color:
        if token.startswith("bg-") or token.startswith("from-") or token.startswith("to-"):
            return f"background-color:{color}"
        if token.startswith("text-"):
            return f"color:{color}"
        if token.startswith("border-"):
            return f"border-color:{color}"
    grad = re.match(r"^(from|to|via)-([\w-]+-\d+)$", token)
    if grad:
        c = TAILWIND_PALETTE.get(grad.group(2))
        if c and grad.group(1) == "from":
            return f"--tw-gradient-from:{c}"
    opacity = re.match(r"^opacity-(\d+)$", token)
    if opacity:
        return f"opacity:{int(opacity.group(1))/100}"
    hover = re.match(r"^hover:(.+)$", token)
    if hover:
        base = _css_for_class(hover.group(1))
        if base and "background" in base:
            return f"transition:background-color .2s ease"
        if base and "shadow" in base:
            return "transition:box-shadow .2s ease"
    return None


def _build_stylesheet(html: str) -> str:
    rules: list[str] = [
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}",
        "html{scroll-behavior:smooth}",
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.5;",
        "background:#0a0a0f;color:#e2e8f0;min-height:100vh}",
        "a{color:inherit;text-decoration:none}",
        "a:hover{opacity:.9}",
        "button{font:inherit;cursor:pointer;border:none;background:transparent}",
        "img,video{max-width:100%;height:auto}",
        "#cf-demo-root{min-height:100vh;width:100%}",
        ".cf-demo-banner{padding:.5rem 1rem;background:rgba(0,0,0,.45);",
        "border-bottom:1px solid rgba(34,211,238,.25);font-size:.65rem;",
        "letter-spacing:.12em;text-transform:uppercase;color:#22d3ee}",
    ]
    responsive_tokens: list[str] = []
    for token in sorted(_collect_classes(html)):
        if token in RESPONSIVE_CSS:
            responsive_tokens.append(token)
            continue
        decl = _css_for_class(token)
        if decl:
            safe = re.sub(r"[^a-zA-Z0-9_-]", r"\\$0", token)
            rules.append(f".{safe}{{{decl}}}")
    if responsive_tokens:
        rules.append("@media (min-width:768px){")
        for token in responsive_tokens:
            decl = RESPONSIVE_CSS[token]
            safe = re.sub(r"[^a-zA-Z0-9_:]", r"\\$0", token)
            rules.append(f".{safe}{{{decl}}}")
        rules.append("}")
    return "\n".join(rules)


_INTERACTION_SCRIPT = """
document.querySelectorAll('button').forEach(function(btn) {
  if (btn.dataset.cfBound) return;
  btn.dataset.cfBound = '1';
  btn.addEventListener('click', function() {
    btn.classList.toggle('ring-2');
  });
});
document.querySelectorAll('a[href^="#"]').forEach(function(a) {
  a.addEventListener('click', function(e) {
    var id = a.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if (el) { e.preventDefault(); el.scrollIntoView({ behavior: 'smooth' }); }
  });
});
"""


def build_static_site_html(source: str, *, title: str = "Démo CyberForge") -> str:
    """Page HTML complète, scrollable et interactive (sans CDN)."""
    jsx = _extract_return_jsx(source)
    body_inner = _jsx_to_html(jsx) if jsx else "<p>Contenu vide</p>"
    styles = _build_stylesheet(body_inner)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape_html(title)}</title>
  <style>{styles}</style>
</head>
<body>
  <p class="cf-demo-banner">Démo client · lecture seule · CyberForge</p>
  <div id="cf-demo-root">
    {body_inner}
  </div>
  <script>{_INTERACTION_SCRIPT}</script>
</body>
</html>"""
