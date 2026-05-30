"""Application de la palette toolbox aux projets générés (CSS, fonts, package.json)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from agents.architect_agent import ArchitectPlan
from tools.codegen_service import CodeGenerateResult, GeneratedFile


def hex_to_hsl_channels(hex_color: str) -> str:
    """Convertit #RRGGBB en canaux HSL « H S% L% » (shadcn / Tailwind)."""
    normalized = hex_color.strip().lstrip("#")
    if len(normalized) != 6:
        return "199 89% 48%"
    try:
        r = int(normalized[0:2], 16) / 255
        g = int(normalized[2:4], 16) / 255
        b = int(normalized[4:6], 16) / 255
    except ValueError:
        return "199 89% 48%"

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    h = 0.0
    s = 0.0
    lightness = (max_c + min_c) / 2

    if max_c != min_c:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if lightness > 0.5 else d / (max_c + min_c)
        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6

    return f"{round(h * 360)} {round(s * 100)}% {round(lightness * 100)}%"


def google_fonts_stylesheet_url(heading_font: str, body_font: str) -> str:
    families: list[str] = []

    def _family(name: str) -> str:
        return quote_plus(name.strip().replace(" ", "+"))

    if heading_font.strip():
        families.append(f"family={_family(heading_font)}:wght@400;500;600;700")
    body = body_font.strip()
    if body and body != heading_font.strip():
        families.append(f"family={_family(body)}:wght@400;500;600")
    if not families:
        return ""
    return f"https://fonts.googleapis.com/css2?{'&'.join(families)}&display=swap"


def build_toolbox_builder_context(plan: ArchitectPlan) -> str:
    """Bloc de consignes transmis à BuilderAI / CoreMind."""
    if not plan.palette or not plan.typo:
        return ""

    primary = plan.palette.primary
    secondary = plan.palette.secondary
    accent = plan.palette.accent
    heading = plan.typo.heading
    body = plan.typo.body
    composants = ", ".join(plan.composants_recommandes) if plan.composants_recommandes else "hero, contact"

    return (
        f"Secteur toolbox : {plan.secteur or 'général'}.\n"
        f"Palette obligatoire — primary {primary}, secondary {secondary}, accent {accent}.\n"
        f"Typographies Google Fonts — titres : {heading}, corps : {body}.\n"
        f"Composants UI à prioriser (shadcn/ui + Framer Motion) : {composants}.\n"
        "Utilise des variables CSS --cf-primary, --cf-secondary, --cf-accent et mappe-les au thème.\n"
        "Inclus framer-motion pour les animations d'entrée (motion.div / motion.section).\n"
        "Stack : React, TypeScript, Tailwind, composants shadcn/ui.\n\n"
    )


def _css_variables_block(plan: ArchitectPlan) -> str:
    p = plan.palette
    assert p is not None
    primary_hsl = hex_to_hsl_channels(p.primary)
    secondary_hsl = hex_to_hsl_channels(p.secondary)
    accent_hsl = hex_to_hsl_channels(p.accent)
    heading = plan.typo.heading if plan.typo else "Inter"
    body = plan.typo.body if plan.typo else "Inter"

    return f"""/* CyberForge toolbox — secteur {plan.secteur or "default"} */
:root {{
  --cf-primary: {p.primary};
  --cf-secondary: {p.secondary};
  --cf-accent: {p.accent};
  --cf-font-heading: '{heading}', serif;
  --cf-font-body: '{body}', sans-serif;
  --primary: {primary_hsl};
  --secondary: {secondary_hsl};
  --accent: {accent_hsl};
  --ring: {primary_hsl};
}}
body {{
  font-family: var(--cf-font-body);
}}
h1, h2, h3, h4 {{
  font-family: var(--cf-font-heading);
}}
"""


def _inject_fonts_link(html: str, plan: ArchitectPlan) -> str:
    if not plan.typo:
        return html
    url = google_fonts_stylesheet_url(plan.typo.heading, plan.typo.body)
    if not url:
        return html
    link = f'<link rel="stylesheet" href="{url}" />\n'
    if url in html:
        return html
    if "</head>" in html.lower():
        return re.sub(r"</head>", f"  {link}</head>", html, count=1, flags=re.I)
    return link + html


def _merge_package_json(content: str, plan: ArchitectPlan) -> str:
    try:
        pkg = json.loads(content)
    except json.JSONDecodeError:
        return content
    if not isinstance(pkg, dict):
        return content
    deps = pkg.setdefault("dependencies", {})
    if isinstance(deps, dict) and "framer-motion" not in deps:
        deps["framer-motion"] = "^11.0.0"
    return json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"


def _patch_file_content(path: str, content: str, plan: ArchitectPlan) -> str:
    lower = path.lower()
    css_block = _css_variables_block(plan)

    if lower.endswith(".css"):
        if "--cf-primary" in content:
            return content
        return css_block + "\n" + content

    if lower.endswith(".html"):
        patched = _inject_fonts_link(content, plan)
        if "--cf-primary" not in patched and "<style>" in patched.lower():
            patched = re.sub(
                r"(<style[^>]*>)",
                rf"\1\n{css_block}",
                patched,
                count=1,
                flags=re.I,
            )
        elif "--cf-primary" not in patched:
            patched = patched.replace("</head>", f"  <style>\n{css_block}\n  </style>\n</head>", 1)
        return patched

    if lower.endswith("package.json"):
        return _merge_package_json(content, plan)

    return content


def apply_toolbox_to_generation(
    generation: CodeGenerateResult,
    plan: ArchitectPlan | None,
) -> CodeGenerateResult:
    """Injecte palette, polices et framer-motion dans les fichiers générés."""
    if not plan or not plan.palette:
        return generation

    updated_files: list[GeneratedFile] = []
    touched = False
    for file in generation.files:
        new_content = _patch_file_content(file.path, file.content, plan)
        if new_content != file.content:
            touched = True
        updated_files.append(GeneratedFile(path=file.path, content=new_content))

    primary_code = generation.code
    if primary_code and "--cf-primary" not in primary_code:
        if primary_code.lstrip().startswith("<!"):
            primary_code = _inject_fonts_link(primary_code, plan)
            if "<style>" not in primary_code.lower():
                primary_code = primary_code.replace(
                    "</head>",
                    f"  <style>\n{_css_variables_block(plan)}\n  </style>\n</head>",
                    1,
                )
        else:
            primary_code = _css_variables_block(plan) + "\n" + primary_code
        touched = True

    if not touched and not any(f.path.endswith(".css") for f in updated_files):
        updated_files.append(
            GeneratedFile(path="src/toolbox-theme.css", content=_css_variables_block(plan))
        )
        touched = True

    stack = list(generation.stack)
    for tag in ("framer-motion", "shadcn-ui"):
        if tag not in stack:
            stack.append(tag)

    return CodeGenerateResult(
        summary=generation.summary,
        code=primary_code,
        files=updated_files,
        stack=stack,
        model=generation.model,
        provider=generation.provider,
        demo_seed=generation.demo_seed,
    )


def apply_toolbox_vitrine_scaffold(output_dir: Path, plan: ArchitectPlan | None) -> None:
    """Applique palette / typos / framer-motion au scaffold Next.js vitrine."""
    if not plan or not plan.palette:
        return

    root = Path(output_dir)
    pkg_path = root / "package.json"
    if pkg_path.is_file():
        pkg_path.write_text(
            _merge_package_json(pkg_path.read_text(encoding="utf-8"), plan),
            encoding="utf-8",
        )

    globals_path = root / "app" / "globals.css"
    if globals_path.is_file():
        css = globals_path.read_text(encoding="utf-8")
        p = plan.palette
        primary_hsl = hex_to_hsl_channels(p.primary)
        secondary_hsl = hex_to_hsl_channels(p.secondary)
        accent_hsl = hex_to_hsl_channels(p.accent)
        replacements = {
            r"--primary:\s*[^;]+;": f"--primary: {primary_hsl};",
            r"--secondary:\s*[^;]+;": f"--secondary: {secondary_hsl};",
            r"--accent:\s*[^;]+;": f"--accent: {accent_hsl};",
            r"--ring:\s*[^;]+;": f"--ring: {primary_hsl};",
        }
        for pattern, repl in replacements.items():
            css, count = re.subn(pattern, repl, css, count=1)
            if count == 0 and "/* toolbox */" not in css:
                css = css.replace(":root {", f":root {{\n    /* toolbox */", 1)
        if "/* toolbox */" not in css:
            css = _css_variables_block(plan) + "\n" + css
        globals_path.write_text(css, encoding="utf-8")

    layout_path = root / "app" / "layout.tsx"
    if layout_path.is_file() and plan.typo:
        layout = layout_path.read_text(encoding="utf-8")
        url = google_fonts_stylesheet_url(plan.typo.heading, plan.typo.body)
        if url and url not in layout:
            layout = layout.replace(
                'import "./globals.css";',
                f'import "./globals.css";\n\nexport const toolboxFontsUrl = "{url}";',
                1,
            )
        p = plan.palette
        style_block = (
            f'          "--primary": "{hex_to_hsl_channels(p.primary)}",\n'
            f'          "--ring": "{hex_to_hsl_channels(p.primary)}",\n'
            f'          "--secondary": "{hex_to_hsl_channels(p.secondary)}",\n'
            f'          "--accent": "{hex_to_hsl_channels(p.accent)}",\n'
        )
        if '"--primary"' in layout:
            layout = re.sub(
                r'("--primary":\s*)"[^"]*"',
                rf'\1"{hex_to_hsl_channels(p.primary)}"',
                layout,
                count=1,
            )
            layout = re.sub(
                r'("--ring":\s*)"[^"]*"',
                rf'\1"{hex_to_hsl_channels(p.primary)}"',
                layout,
                count=1,
            )
        layout_path.write_text(layout, encoding="utf-8")

    site_json = root / "content" / "site.json"
    if site_json.is_file():
        try:
            data = json.loads(site_json.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("meta"), dict):
                data["meta"]["primaryColor"] = plan.palette.primary
                site_json.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        except json.JSONDecodeError:
            pass


def build_toolbox_content_agent_block(plan: ArchitectPlan | None) -> str:
    """Contexte toolbox pour VitrineContentAI."""
    if not plan or not plan.palette:
        return ""
    composants = ", ".join(plan.composants_recommandes or [])
    return (
        f"\nPalette secteur ({plan.secteur}) : primary {plan.palette.primary}, "
        f"secondary {plan.palette.secondary}, accent {plan.palette.accent}.\n"
        f"Typographies : {plan.typo.heading if plan.typo else ''} / {plan.typo.body if plan.typo else ''}.\n"
        f"Sections recommandées : {composants}.\n"
    )
