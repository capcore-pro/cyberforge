"""
Helpers qualité démo — conversion génération ↔ HTML aperçu.
"""

from __future__ import annotations

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.demo_template_service import TEMPLATE_MODEL, TEMPLATE_PROVIDER, build_html_from_seed, heuristic_demo_seed
from tools.standalone_demo_html import build_task_manager_standalone_html

_TEMPLATE_PROVIDERS = frozenset({TEMPLATE_PROVIDER, "cyberforge"})


def _is_prefab_template_generation(generation: CodeGenerateResult) -> bool:
    return (
        generation.provider in _TEMPLATE_PROVIDERS
        and generation.model == TEMPLATE_MODEL
    )


def preview_html_from_generation(
    generation: CodeGenerateResult,
    *,
    title: str = "Démo CyberForge",
) -> str:
    """HTML d'aperçu — toujours le template premium pour les démos client."""
    if _is_prefab_template_generation(generation):
        code = (generation.code or "").strip()
        if code and "<html" in code.lower():
            return code
    files = [{"path": f.path, "content": f.content} for f in generation.files]
    html_file = next(
        (f for f in files if f["path"].lower().endswith(".html")),
        None,
    )
    if html_file and len(html_file["content"]) > 600:
        return html_file["content"]
    seed = heuristic_demo_seed(
        generation.summary or title,
        project_type_label=title,
    )
    return build_html_from_seed(seed)


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
