"""Injection du panneau CMS client dans les projets générés."""

from __future__ import annotations

import re
from pathlib import Path

from config import Settings, get_settings
from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.cms_markup import annotate_file_content

CMS_BUILDER_HINT = (
    "Marqueurs CMS CyberForge — le post-traitement ajoute aussi data-cms automatiquement ; "
    "vous pouvez les placer explicitement sur le contenu éditorial :\n"
    '- data-cms="text" data-cms-key="<clé>" sur h1, h2, h3, p, button, a\n'
    '- data-cms="image" data-cms-key="<clé>" sur img et divs avec background-image\n'
    '- data-cms="color" data-cms-key="<clé>" sur éléments avec variables --primary / --secondary / --accent\n'
    "Le script cms-panel.js est injecté dans le <head> de chaque livrable.\n"
)

_INJECTABLE_EXTENSIONS = (".html", ".htm", ".tsx", ".jsx", ".css")


def cms_panel_script_url(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    return f"{resolved.backend_public_url.rstrip('/')}/cms/panel.js"


def cms_panel_head_snippet(*, backend_url: str, project_id: str | None = None) -> str:
    base = backend_url.rstrip("/")
    pid = (project_id or "").strip()
    return (
        f'<meta name="cyberforge-cms-project-id" content="{pid}" />\n'
        f'<meta name="cyberforge-cms-api" content="{base}/api" />\n'
        f'<script src="{base}/cms/panel.js" defer></script>\n'
    )


def inject_cms_panel_html(html: str, *, backend_url: str, project_id: str | None = None) -> str:
    html = annotate_file_content("index.html", html)
    snippet = cms_panel_head_snippet(backend_url=backend_url, project_id=project_id)
    if "cms/panel.js" in html:
        return html
    if "</head>" in html.lower():
        return re.sub(r"</head>", snippet + "</head>", html, count=1, flags=re.I)
    if "<body" in html.lower():
        return re.sub(r"<body", snippet + "<body", html, count=1, flags=re.I)
    return snippet + html


def inject_cms_vitrine_layout(layout: str, *, backend_url: str, project_id: str | None) -> str:
    layout = annotate_file_content("layout.tsx", layout)
    pid = (project_id or "").strip()
    base = backend_url.rstrip("/")
    if "cyberforge-cms-project-id" in layout:
        layout = re.sub(
            r'<meta name="cyberforge-cms-project-id" content="[^"]*"',
            f'<meta name="cyberforge-cms-project-id" content="{pid}"',
            layout,
            count=1,
        )
        if "cms/panel.js" not in layout:
            script = f'<script src="{base}/cms/panel.js" defer></script>\n'
            layout = layout.replace("</head>", f"      {script}</head>", 1)
        return layout

    head_block = f"""
      <head>
        <meta name="cyberforge-cms-project-id" content="{pid}" />
        <meta name="cyberforge-cms-api" content="{base}/api" />
        <script src="{base}/cms/panel.js" defer></script>
      </head>"""

    if re.search(r"<html[^>]*>\s*<head>", layout, flags=re.I):
        if "cms/panel.js" not in layout:
            layout = re.sub(
                r"(</head>)",
                f'        <script src="{base}/cms/panel.js" defer></script>\n      \\1',
                layout,
                count=1,
                flags=re.I,
            )
    else:
        layout = re.sub(
            r"(<html[^>]*>)",
            rf"\1{head_block}",
            layout,
            count=1,
            flags=re.I,
        )

    if pid and "data-cms-project-id" not in layout:
        layout = re.sub(
            r"(<body[^>]*)>",
            rf'\1 data-cms-project-id="{pid}">',
            layout,
            count=1,
            flags=re.I,
        )
    return layout


def apply_cms_panel_vitrine_scaffold(
    output_dir: Path,
    *,
    project_id: str | None = None,
    settings: Settings | None = None,
) -> None:
    resolved = settings or get_settings()
    root = Path(output_dir)
    for rel in _INJECTABLE_EXTENSIONS:
        for path in root.rglob(f"*{rel}"):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            annotated = annotate_file_content(str(path.relative_to(root)), text)
            if annotated != text:
                path.write_text(annotated, encoding="utf-8")

    layout_path = root / "app" / "layout.tsx"
    if layout_path.is_file():
        text = layout_path.read_text(encoding="utf-8")
        patched = inject_cms_vitrine_layout(
            text,
            backend_url=resolved.backend_public_url,
            project_id=project_id,
        )
        if patched != text:
            layout_path.write_text(patched, encoding="utf-8")


def apply_cms_panel_to_generation(
    generation: CodeGenerateResult,
    *,
    project_id: str | None = None,
    settings: Settings | None = None,
) -> CodeGenerateResult:
    resolved = settings or get_settings()
    backend_url = resolved.backend_public_url
    updated: list[GeneratedFile] = []
    primary = generation.code
    script_injected = False

    for file in generation.files:
        content = file.content
        lower = file.path.lower()
        if any(lower.endswith(ext) for ext in _INJECTABLE_EXTENSIONS):
            content = annotate_file_content(file.path, content)
        if lower.endswith(".html") or lower.endswith(".htm"):
            content = inject_cms_panel_html(
                content, backend_url=backend_url, project_id=project_id
            )
            script_injected = True
        elif lower.endswith("layout.tsx"):
            content = inject_cms_vitrine_layout(
                content, backend_url=backend_url, project_id=project_id
            )
            script_injected = True
        elif lower.endswith((".tsx", ".jsx")) and "cms/panel.js" not in content:
            if "</head>" in content.lower():
                snippet = cms_panel_head_snippet(
                    backend_url=backend_url, project_id=project_id
                )
                content = re.sub(
                    r"</head>", snippet + "</head>", content, count=1, flags=re.I
                )
                script_injected = True
        updated.append(GeneratedFile(path=file.path, content=content))

    if primary and primary.lstrip().startswith("<!"):
        primary = inject_cms_panel_html(
            primary, backend_url=backend_url, project_id=project_id
        )
        script_injected = True
    elif primary and not script_injected:
        primary = inject_cms_panel_html(
            primary, backend_url=backend_url, project_id=project_id
        )

    return CodeGenerateResult(
        summary=generation.summary,
        code=primary,
        files=updated,
        stack=list(generation.stack),
        model=generation.model,
        provider=generation.provider,
        demo_seed=generation.demo_seed,
    )
