"""
Compat — délègue au pipeline unique (tools.demo_pipeline).
Source de vérité unique : le HTML déployé = celui de la génération si valide.
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
from tools.generation_sources import is_usable_preview_html

_HTML_PATHS = frozenset({INDEX_HTML_PATH, "index.html"})


def _extract_html_from_generation(generation: CodeGenerateResult) -> str | None:
    """Extrait index.html depuis files ou code."""
    for f in generation.files:
        if f.path in _HTML_PATHS:
            content = (f.content or "").strip()
            if content:
                return content
    code = (generation.code or "").strip()
    return code or None


def preview_html_from_generation(
    generation: CodeGenerateResult,
    *,
    title: str = "Démo CyberForge",
    user_prompt: str | None = None,
) -> str:
    """
    Retourne le HTML livrable — sans re-rendu template si le LLM/pipeline
    a déjà produit un document HTML valide.
    """
    raw = _extract_html_from_generation(generation)
    if raw and is_usable_preview_html(raw):
        return raw

    prompt = (user_prompt or generation.summary or title).strip()

    # Chemin template premium : seed explicite (client_demo nominal)
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
        template = normalize_template_id(seed.template)
        html = build_html_from_seed(seed)
        if is_valid_demo_html(html, template):
            return html

    # Dernier recours : HTML brut même partiel, ou heuristique seed
    if raw:
        return raw

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
