"""
Helpers qualité démo — conversion génération ↔ HTML aperçu.
"""

from __future__ import annotations

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.demo_preview_html import build_demo_preview_html


def preview_html_from_generation(
    generation: CodeGenerateResult,
    *,
    title: str = "Démo CyberForge",
) -> str:
    """Construit le HTML livrable tel qu'affiché au client (sans gate mot de passe)."""
    files = [{"path": f.path, "content": f.content} for f in generation.files]
    return build_demo_preview_html(files, title=title, code=generation.code)


def code_result_from_html(
    html: str,
    *,
    summary: str,
    model: str,
    provider: str,
) -> CodeGenerateResult:
    """Emballe un HTML final dans CodeGenerateResult."""
    return CodeGenerateResult(
        summary=summary,
        code=html,
        files=[GeneratedFile(path="index.html", content=html)],
        stack=["html", "css", "javascript"],
        model=model,
        provider=provider,
    )
