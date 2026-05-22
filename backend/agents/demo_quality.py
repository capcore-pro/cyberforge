"""
Compat — délègue au pipeline unique (tools.demo_pipeline).
"""

from __future__ import annotations

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.demo_pipeline import INDEX_HTML_PATH
from tools.demo_template_service import (
    build_html_from_seed,
    heuristic_demo_seed,
    seed_from_dict,
    seed_to_code_result,
)


def preview_html_from_generation(
    generation: CodeGenerateResult,
    *,
    title: str = "Démo CyberForge",
    user_prompt: str | None = None,
) -> str:
    """Toujours le HTML TaskFlow du pipeline (jamais JSX / conversion)."""
    if generation.demo_seed:
        return build_html_from_seed(seed_from_dict(generation.demo_seed))
    prompt = (user_prompt or generation.summary or title).strip()
    return build_html_from_seed(
        heuristic_demo_seed(prompt, project_type_label=title),
    )


def code_result_from_html(
    html: str,
    *,
    summary: str,
    model: str,
    provider: str,
) -> CodeGenerateResult:
    return CodeGenerateResult(
        summary=summary,
        code=html,
        files=[GeneratedFile(path=INDEX_HTML_PATH, content=html)],
        stack=["html", "css", "javascript"],
        model=model,
        provider=provider,
    )
