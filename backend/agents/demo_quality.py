"""
Compat — délègue au pipeline unique (tools.demo_pipeline).
Aperçu local : conserve le template choisi par ArchitectAI / détection prompt.
"""

from __future__ import annotations

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.demo_pipeline import INDEX_HTML_PATH
from tools.demo_template_service import (
    align_seed_template,
    build_html_from_seed,
    heuristic_demo_seed,
    is_valid_demo_html,
    normalize_template_id,
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
    Aperçu local Générateur — template premium aligné sur la seed du projet
    (CRM, dashboard, landing, facturation ou TaskFlow).
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

    template = normalize_template_id(seed.template)
    html = build_html_from_seed(seed)
    if not is_valid_demo_html(html, template):
        raise ValueError(
            f"Aperçu invalide pour le template « {template} » (marqueur manquant)."
        )
    return html


def preview_html_from_seed_dict(
    seed_data: dict[str, object],
    *,
    title: str = "Démo CyberForge",
    user_prompt: str = "",
) -> str:
    """Aperçu premium à partir d'une seed JSON (personnalisation temps réel)."""
    seed = align_seed_template(
        seed_from_dict(
            seed_data,
            prompt=user_prompt,
            project_type_label=title,
        ),
        user_prompt or title,
        project_type_label=title,
    )
    template = normalize_template_id(seed.template)
    html = build_html_from_seed(seed)
    if not is_valid_demo_html(html, template):
        raise ValueError(
            f"Aperçu invalide pour le template « {template} » (marqueur manquant)."
        )
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
