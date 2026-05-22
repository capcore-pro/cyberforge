"""
Compat — délègue au pipeline unique (tools.demo_pipeline).
"""

from __future__ import annotations

from dataclasses import replace

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.demo_pipeline import INDEX_HTML_PATH
from tools.demo_template_service import (
    TEMPLATE_TASKFLOW,
    align_seed_template,
    build_html_from_seed,
    heuristic_demo_seed,
    is_valid_demo_html,
    seed_from_dict,
    seed_to_code_result,
)


def preview_html_from_generation(
    generation: CodeGenerateResult,
    *,
    title: str = "Démo CyberForge",
    user_prompt: str | None = None,
) -> str:
    """
    Aperçu local Générateur — toujours le template TaskFlow premium,
    personnalisé avec la seed du projet (titre, marque, tâches).
    """
    prompt = (user_prompt or generation.summary or title).strip()
    if generation.demo_seed:
        seed = align_seed_template(
            seed_from_dict(
                generation.demo_seed,
                prompt=prompt,
                project_type_label=title,
            ),
            prompt,
            project_type_label=title,
        )
    else:
        seed = heuristic_demo_seed(prompt, project_type_label=title)

    preview_seed = replace(seed, template=TEMPLATE_TASKFLOW)
    html = build_html_from_seed(preview_seed)
    if not is_valid_demo_html(html, TEMPLATE_TASKFLOW):
        raise ValueError("Aperçu TaskFlow invalide (saas-shell manquant).")
    return html


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
