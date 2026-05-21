"""
Conversion TSX/JSX → document HTML statique pour les démos client.
Même logique que frontend/src/lib/preview-html.ts (maquette visuelle).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TAILWIND_PALETTE: dict[str, str] = {
    "slate-950": "#020617",
    "slate-900": "#0f172a",
    "gray-900": "#111827",
    "gray-800": "#1f2937",
    "zinc-900": "#18181b",
    "neutral-900": "#171717",
    "black": "#000000",
    "white": "#f8fafc",
    "violet-600": "#7c3aed",
    "violet-500": "#8b5cf6",
    "purple-600": "#9333ea",
    "purple-500": "#a855f7",
    "fuchsia-500": "#d946ef",
    "cyan-400": "#22d3ee",
    "cyan-500": "#06b6d4",
    "teal-400": "#2dd4bf",
    "emerald-400": "#34d399",
    "green-500": "#22c55e",
    "amber-400": "#fbbf24",
    "orange-500": "#f97316",
    "red-400": "#f87171",
    "rose-500": "#f43f5e",
    "blue-500": "#3b82f6",
    "indigo-600": "#4f46e5",
}

NOISE_STRINGS = re.compile(
    r"^(true|false|null|undefined|react|typescript|tailwind|className|onClick|flex|grid|"
    r"block|inline|relative|absolute|fixed|w-full|h-full|min-h-screen|px-\d|py-\d|mx-auto|"
    r"items-center|justify-center|gap-\d|rounded|border|shadow|text-(xs|sm|base|lg|xl|2xl|3xl|4xl)|"
    r"font-(bold|semibold|medium)|transition|hover:|focus:|md:|lg:|sm:)",
    re.I,
)


@dataclass
class PreviewSection:
    heading: str
    lines: list[str]


@dataclass
class PreviewColorSwatch:
    label: str
    value: str


@dataclass
class PreviewMockup:
    title: str
    subtitle: str
    sections: list[PreviewSection] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    colors: list[PreviewColorSwatch] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def escape_attr(text: str) -> str:
    return escape_html(text).replace("'", "&#39;")


def _is_complete_html(content: str) -> bool:
    lower = content.strip().lower()
    return "<html" in lower and "<body" in lower


def _strip_jsx(fragment: str) -> str:
    return _clean_label(re.sub(r"<[^>]+>", " ", fragment))


def _clean_label(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\{[^}]+\}", " ", raw)).strip()


def _looks_like_code_token(text: str) -> bool:
    if NOISE_STRINGS.match(text):
        return True
    if re.match(r"^[\w./@-]+$", text) and " " not in text:
        return True
    if text in ("src", "className", "import", "export", "return", "function", "const", "let"):
        return True
    return False


def _looks_like_price_or_fragment(text: str) -> bool:
    if re.match(r"^[\d,.\s€$£+-]+$", text):
        return True
    if text in ("(", ")", "{", "}", "=>", "...", "key"):
        return True
    return len(text) < 4


def _extract_map_literal_items(code: str) -> list[str]:
    """Lit les objets { name, desc, price } typiques d'un .map JSX."""
    items: list[str] = []
    for match in re.finditer(
        r"name\s*:\s*['\"]([^'\"]+)['\"][^}]*?"
        r"(?:desc\s*:\s*['\"]([^'\"]+)['\"])?[^}]*?"
        r"(?:price\s*:\s*['\"]([^'\"]+)['\"])?",
        code,
        re.I | re.S,
    ):
        name = match.group(1).strip()
        desc = (match.group(2) or "").strip()
        price = (match.group(3) or "").strip()
        line = name
        if desc:
            line += f" — {desc}"
        if price:
            line += f" ({price})"
        if name and line not in items:
            items.append(line)
    return items


def _extract_headings(code: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for match in re.finditer(r"<h([1-3])[^>]*>([\s\S]*?)</h\1>", code, re.I):
        text = _strip_jsx(match.group(2))
        if text:
            found.append((int(match.group(1)), text))
    return found


def _extract_readable_strings(code: str) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r">([^<>{}]+)<", code):
        text = _clean_label(match.group(1))
        if text and text not in seen:
            seen.add(text)
            results.append(text)

    for match in re.finditer(r"""["'`]([^"'`\n]{4,120})["'`]""", code):
        text = _clean_label(match.group(1))
        if text and text not in seen and not _looks_like_code_token(text):
            seen.add(text)
            results.append(text)

    return results


def _extract_class_names(code: str) -> list[str]:
    classes: list[str] = []
    for match in re.finditer(
        r'className\s*=\s*(?:\{`([^`]+)`\}|"([^"]+)"|\'([^\']+)\')',
        code,
    ):
        value = match.group(1) or match.group(2) or match.group(3)
        if value:
            classes.append(value)
    return classes


def _extract_colors(class_strings: list[str]) -> list[PreviewColorSwatch]:
    swatches: list[PreviewColorSwatch] = []
    seen: set[str] = set()

    for block in class_strings:
        for token in block.split():
            color_match = re.match(
                r"^(?:bg|text|from|to|via|border|ring)-([a-z]+-\d{2,3}|[a-z]+)$",
                token,
            )
            if not color_match:
                continue
            label = color_match.group(1)
            value = TAILWIND_PALETTE.get(label)
            if not value or label in seen:
                continue
            seen.add(label)
            swatches.append(PreviewColorSwatch(label=label, value=value))

    if not swatches:
        swatches = [
            PreviewColorSwatch(label="fond", value="#0a0a0f"),
            PreviewColorSwatch(label="accent", value="#22d3ee"),
            PreviewColorSwatch(label="violet", value="#a855f7"),
        ]
    return swatches


def _extract_buttons(code: str, strings: list[str]) -> list[str]:
    buttons: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"<button[^>]*>([\s\S]*?)</button>", code, re.I):
        label = _strip_jsx(match.group(1))
        if label and label not in seen:
            seen.add(label)
            buttons.append(label)

    cta_re = re.compile(
        r"réserver|contact|menu|acheter|commencer|découvrir|voir|envoyer|inscri|login|sign|cta",
        re.I,
    )
    for s in strings:
        if len(s) < 28 and cta_re.search(s) and s not in seen:
            seen.add(s)
            buttons.append(s)

    return buttons


def _extract_layout_hints(class_strings: list[str]) -> list[str]:
    hints: list[str] = []
    joined = " ".join(class_strings)
    if re.search(r"grid", joined, re.I):
        hints.append("Grille")
    if re.search(r"flex", joined, re.I):
        hints.append("Flex")
    if re.search(r"hero|banner", joined, re.I):
        hints.append("Hero")
    if re.search(r"dark|slate-9|gray-9|zinc-9", joined, re.I):
        hints.append("Thème sombre")
    if re.search(r"gradient|from-|to-", joined, re.I):
        hints.append("Dégradés")
    if re.search(r"rounded|shadow", joined, re.I):
        hints.append("Cartes")
    if re.search(r"md:|lg:|sm:", joined):
        hints.append("Responsive")
    return hints[:6]


def extract_preview_mockup(source: str, *, default_title: str = "Prototype généré") -> PreviewMockup:
    code = re.sub(r"/\*[\s\S]*?\*/", "", source)
    code = re.sub(r"//.*$", "", code, flags=re.M)

    headings = _extract_headings(code)
    strings = _extract_readable_strings(code)
    class_names = _extract_class_names(code)
    colors = _extract_colors(class_names)
    buttons = _extract_buttons(code, strings)

    map_items = _extract_map_literal_items(code)

    title = default_title
    for level, text in headings:
        if level == 1:
            title = text
            break
    if title == default_title:
        for s in strings:
            if 4 < len(s) < 80 and not _looks_like_price_or_fragment(s):
                title = s
                break

    subtitle = "Aperçu simplifié — structure et ambiance du site généré."
    for s in strings:
        if s != title and 12 < len(s) < 140:
            subtitle = s
            break

    section_headings = [text for level, text in headings if level >= 2 and text != title]
    body_lines = [
        s
        for s in strings
        if s not in (title, subtitle)
        and s not in section_headings
        and s not in buttons
        and not _looks_like_price_or_fragment(s)
    ][:8]

    sections: list[PreviewSection] = []
    if map_items:
        sections.append(PreviewSection(heading="Contenu généré", lines=map_items[:8]))
    if section_headings:
        for heading in section_headings[:5]:
            lines = body_lines[:2]
            del body_lines[:2]
            sections.append(
                PreviewSection(
                    heading=heading,
                    lines=lines or ["Contenu de section généré par CoreMindAI."],
                )
            )
    elif body_lines:
        sections.append(PreviewSection(heading="Contenu principal", lines=body_lines[:4]))
    else:
        sections.append(
            PreviewSection(
                heading="Structure détectée",
                lines=[
                    "Le composant React contient une mise en page Tailwind.",
                    "Ouvrez le code source pour le détail des interactions.",
                ],
            )
        )

    return PreviewMockup(
        title=title,
        subtitle=subtitle,
        sections=sections,
        buttons=buttons[:6],
        colors=colors[:8],
        hints=_extract_layout_hints(class_names),
    )


def build_mockup_preview_html(mockup: PreviewMockup) -> str:
    primary = mockup.colors[0].value if mockup.colors else "#0f172a"
    accent = next(
        (c.value for c in mockup.colors if re.search(r"cyan|violet|purple|teal|fuchsia", c.label, re.I)),
        "#22d3ee",
    )
    accent2 = next(
        (c.value for c in mockup.colors if re.search(r"violet|purple|fuchsia", c.label, re.I)),
        "#a855f7",
    )

    sections_html = "".join(
        f"""
      <section class="mock-section">
        <h2>{escape_html(s.heading)}</h2>
        {''.join(f'<p>{escape_html(line)}</p>' for line in s.lines)}
      </section>"""
        for s in mockup.sections
    )

    buttons_html = ""
    if mockup.buttons:
        buttons_html = (
            '<div class="mock-actions">'
            + "".join(
                f'<span class="mock-btn" style="--i:{i}">{escape_html(label)}</span>'
                for i, label in enumerate(mockup.buttons)
            )
            + "</div>"
        )

    palette_html = ""
    if mockup.colors:
        swatches = "".join(
            f'<span class="mock-swatch" title="{escape_attr(c.label)}" '
            f'style="background:{c.value}"></span>'
            for c in mockup.colors
        )
        palette_html = f"""<div class="mock-palette">
        <p class="mock-palette-label">Palette détectée</p>
        <div class="mock-swatches">{swatches}</div>
      </div>"""

    hints_html = ""
    if mockup.hints:
        hints_html = (
            '<ul class="mock-hints">'
            + "".join(f"<li>{escape_html(h)}</li>" for h in mockup.hints)
            + "</ul>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape_html(mockup.title)} — Aperçu</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: {primary};
      color: #e2e8f0;
      min-height: 100vh;
      line-height: 1.5;
    }}
    .mock-banner {{
      padding: 0.5rem 1rem;
      background: rgba(0,0,0,0.35);
      border-bottom: 1px solid rgba(34,211,238,0.25);
      font-size: 0.65rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: {accent};
    }}
    .mock-hero {{
      padding: 2.5rem 1.5rem 2rem;
      background: linear-gradient(135deg, {primary} 0%, {accent2}55 100%);
      border-bottom: 1px solid rgba(168,85,247,0.25);
    }}
    .mock-hero h1 {{
      font-size: clamp(1.5rem, 4vw, 2.25rem);
      font-weight: 800;
      color: {accent};
      text-shadow: 0 0 24px {accent}80;
      margin-bottom: 0.75rem;
    }}
    .mock-hero p {{ color: #94a3b8; max-width: 40rem; font-size: 0.95rem; }}
    .mock-body {{ padding: 1.5rem; max-width: 56rem; margin: 0 auto; }}
    .mock-section {{
      background: rgba(15,23,42,0.65);
      border: 1px solid rgba(148,163,184,0.15);
      border-radius: 0.75rem;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1rem;
    }}
    .mock-section h2 {{
      font-size: 1.1rem;
      color: {accent2};
      margin-bottom: 0.65rem;
      font-weight: 700;
    }}
    .mock-section p {{ color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.4rem; }}
    .mock-actions {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }}
    .mock-btn {{
      display: inline-block;
      padding: 0.5rem 1rem;
      border-radius: 0.5rem;
      background: linear-gradient(90deg, {accent2}, {accent});
      color: #0a0a0f;
      font-size: 0.8rem;
      font-weight: 700;
    }}
    .mock-palette {{ margin-top: 1.25rem; }}
    .mock-palette-label {{
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
      color: #64748b; margin-bottom: 0.5rem;
    }}
    .mock-swatches {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
    .mock-swatch {{
      width: 2rem; height: 2rem; border-radius: 0.35rem;
      border: 1px solid rgba(255,255,255,0.15);
    }}
    .mock-hints {{
      list-style: none; margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.35rem;
    }}
    .mock-hints li {{
      font-size: 0.65rem; padding: 0.25rem 0.5rem; border-radius: 999px;
      border: 1px solid rgba(34,211,238,0.3); color: {accent};
      background: rgba(34,211,238,0.08);
    }}
    .mock-wireframe {{
      margin-top: 1.5rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
    }}
    .mock-card {{
      height: 5rem; border-radius: 0.5rem;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
      border: 1px dashed rgba(148,163,184,0.25);
    }}
  </style>
</head>
<body>
  <p class="mock-banner">Aperçu livrable · CyberForge</p>
  <header class="mock-hero">
    <h1>{escape_html(mockup.title)}</h1>
    <p>{escape_html(mockup.subtitle)}</p>
    {buttons_html}
  </header>
  <main class="mock-body">
    {sections_html}
    {palette_html}
    {hints_html}
    <div class="mock-wireframe" aria-hidden="true">
      <div class="mock-card"></div>
      <div class="mock-card"></div>
      <div class="mock-card"></div>
    </div>
  </main>
</body>
</html>"""


def build_demo_preview_html(
    files: list[dict[str, str]],
    *,
    title: str = "Démo CyberForge",
    code: str | None = None,
) -> str:
    """Produit le HTML final stocké en base pour la page /demo/{token}."""
    from tools.generation_sources import normalize_generation_sources

    files, code = normalize_generation_sources(files, code)
    normalized = [{"path": f["path"].strip(), "content": f["content"]} for f in files if f.get("path")]

    html_file = next((f for f in normalized if re.search(r"\.html?$", f["path"], re.I)), None)
    if html_file and _is_complete_html(html_file["content"]):
        content = html_file["content"]
        if "mock-banner" not in content and "Démo client" not in content:
            return content.replace(
                "<body>",
                '<body><p class="mock-banner" style="padding:0.5rem 1rem;background:#0a0a0f;color:#22d3ee;font-size:0.65rem;">Aperçu livrable · CyberForge</p>',
                1,
            )
        return content

    sources = "\n\n".join(
        f["content"]
        for f in normalized
        if re.search(r"\.(tsx|jsx|ts|js|css)$", f["path"], re.I)
    )
    if not sources.strip() and code:
        sources = code

    if not sources.strip():
        return build_mockup_preview_html(
            PreviewMockup(
                title=title,
                subtitle="Aucun contenu à afficher.",
                sections=[
                    PreviewSection(
                        heading="Livrable vide",
                        lines=["Cette démo ne contient pas de code exploitable."],
                    )
                ],
            )
        )

    from tools.standalone_demo_html import build_standalone_demo_html

    return build_standalone_demo_html(sources, title=title)
