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
    "shadow-lg": "box-shadow:0 10px 25px rgba(0,0,0,.45)",
    "border": "border-width:1px;border-style:solid",
    "overflow-hidden": "overflow:hidden",
    "overflow-auto": "overflow:auto",
    "relative": "position:relative",
    "absolute": "position:absolute",
    "fixed": "position:fixed",
    "inset-0": "inset:0",
    "p-2": "padding:0.5rem",
    "p-4": "padding:1rem",
    "p-6": "padding:1.5rem",
    "p-8": "padding:2rem",
    "px-4": "padding-left:1rem;padding-right:1rem",
    "px-6": "padding-left:1.5rem;padding-right:1.5rem",
    "py-2": "padding-top:0.5rem;padding-bottom:0.5rem",
    "py-4": "padding-top:1rem;padding-bottom:1rem",
    "py-8": "padding-top:2rem;padding-bottom:2rem",
    "py-12": "padding-top:3rem;padding-bottom:3rem",
    "py-16": "padding-top:4rem;padding-bottom:4rem",
    "mt-2": "margin-top:0.5rem",
    "mt-4": "margin-top:1rem",
    "mt-6": "margin-top:1.5rem",
    "mt-8": "margin-top:2rem",
    "mb-2": "margin-bottom:0.5rem",
    "mb-4": "margin-bottom:1rem",
    "mb-6": "margin-bottom:1.5rem",
    "mb-8": "margin-bottom:2rem",
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


def _jsx_to_html(jsx: str) -> str:
    html = jsx
    html = re.sub(r"className\s*=", "class=", html)
    html = re.sub(r"htmlFor\s*=", "for=", html)
    html = re.sub(r"\{`([^`]*)`\}", r"\1", html)
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    html = re.sub(r"\{[^}]*\}", "", html)
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

    # Composants React inconnus → div
    html = re.sub(
        r"<([A-Z][A-Za-z0-9]*)([^>]*)>",
        lambda m: f"<div data-component=\"{escape_attr(m.group(1))}\"{m.group(2)}>",
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
    return None


def _build_stylesheet(html: str) -> str:
    rules: list[str] = [
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}",
        "html{scroll-behavior:smooth}",
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.5;",
        "background:#0a0a0f;color:#e2e8f0;min-height:100vh}",
        "a{color:#22d3ee;text-decoration:none}",
        "a:hover{text-decoration:underline}",
        "button{font:inherit;cursor:pointer}",
        "img,video{max-width:100%;height:auto}",
        "#cf-demo-root{min-height:100vh}",
        ".cf-demo-banner{padding:.5rem 1rem;background:rgba(0,0,0,.45);",
        "border-bottom:1px solid rgba(34,211,238,.25);font-size:.65rem;",
        "letter-spacing:.12em;text-transform:uppercase;color:#22d3ee}",
    ]
    for token in sorted(_collect_classes(html)):
        decl = _css_for_class(token)
        if decl:
            safe = re.sub(r"[^a-zA-Z0-9_-]", r"\\$0", token)
            rules.append(f".{safe}{{{decl}}}")
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
