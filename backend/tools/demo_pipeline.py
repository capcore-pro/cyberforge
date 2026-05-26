"""
Pipeline unique démo client — templates premium + seed → un seul index.html.

Point d'entrée pour CoreMind, POST /demos, aperçu local et Cloudflare.
Pas de génération HTML par LLM, pas de conversion JSX, pas de BugHunter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import Settings, get_settings
from tools.codegen_service import CodeGenerateResult
from tools.demo_template_service import (
    TEMPLATE_LABELS,
    DemoSeedData,
    DemoTemplateService,
    align_seed_template,
    build_html_from_seed,
    is_valid_demo_html,
    seed_as_dict,
    seed_from_dict,
    seed_to_code_result,
)
from tools.standalone_demo_html import wrap_with_password_gate

logger = logging.getLogger(__name__)

INDEX_HTML_PATH = "index.html"


@dataclass(frozen=True)
class ClientDemoDocument:
    """
    Livrable démo unique.

    html : document premium plain (sans gate) — aperçu local + base Cloudflare.
    """

    html: str
    seed: DemoSeedData
    generation: CodeGenerateResult

    @property
    def template(self) -> str:
        return self.seed.template

    @property
    def html_bytes(self) -> int:
        return len(self.html.encode("utf-8"))

    def seed_dict(self) -> dict[str, object]:
        return seed_as_dict(self.seed)


async def build_client_demo_document(
    user_prompt: str,
    *,
    project_type_label: str = "Démo client",
    settings: Settings | None = None,
    seed: DemoSeedData | None = None,
) -> ClientDemoDocument:
    """
    Produit le HTML final premium à partir du prompt (seed LLM ou heuristique).
    """
    svc = DemoTemplateService(settings)
    prompt = user_prompt.strip()
    resolved = seed or await svc.resolve_seed(
        prompt,
        project_type_label=project_type_label,
    )
    resolved = align_seed_template(
        resolved,
        prompt,
        project_type_label=project_type_label,
    )
    html = build_html_from_seed(resolved)
    if not is_valid_demo_html(html, resolved.template):
        raise ValueError(
            f"Pipeline démo : HTML invalide pour le template « {resolved.template} »."
        )

    label = TEMPLATE_LABELS.get(resolved.template, resolved.template)
    summary = (
        f"Démo {resolved.brand_name} — {label}"
        + (" (seed IA)" if resolved.llm_personalized else " (seed locale)")
    )
    generation = seed_to_code_result(resolved, summary=summary + ".")

    logger.info(
        "[DemoPipeline] document prêt | template=%s | brand=%s | bytes=%s | seed_ia=%s",
        resolved.template,
        resolved.brand_name,
        len(html.encode("utf-8")),
        resolved.llm_personalized,
    )
    return ClientDemoDocument(html=html, seed=resolved, generation=generation)


def client_demo_from_seed_dict(
    data: dict[str, object],
    *,
    prompt: str = "",
    project_type_label: str = "",
) -> ClientDemoDocument:
    """Reconstruit le document à partir d'une seed sérialisée (POST /demos)."""
    resolved = seed_from_dict(
        data,
        prompt=prompt,
        project_type_label=project_type_label,
    )
    if prompt.strip() or project_type_label.strip():
        resolved = align_seed_template(
            resolved,
            prompt,
            project_type_label=project_type_label,
        )
    html = build_html_from_seed(resolved)
    if not is_valid_demo_html(html, resolved.template):
        raise ValueError(
            f"Pipeline démo : HTML invalide pour le template « {resolved.template} »."
        )
    label = TEMPLATE_LABELS.get(resolved.template, resolved.template)
    generation = seed_to_code_result(
        resolved,
        summary=f"Démo {resolved.brand_name} — {label}.",
    )
    return ClientDemoDocument(html=html, seed=resolved, generation=generation)


def wrap_demo_for_cloudflare(
    document: ClientDemoDocument,
    password: str,
    *,
    title: str = "Démo CyberForge",
    demo_token: str = "",
    demo_url: str = "",
    api_base_url: str = "",
) -> str:
    """Applique le gate mot de passe pour le déploiement Pages / unlock local."""
    from tools.demo_runtime import inject_demo_runtime_config

    gated = wrap_with_password_gate(document.html, password.strip(), title=title)
    if "cf-password-toggle" not in gated:
        raise ValueError("Gate mot de passe invalide (cf-password-toggle manquant).")
    if demo_token and api_base_url:
        gated = inject_demo_runtime_config(
            gated,
            token=demo_token,
            project_title=title,
            demo_url=demo_url or "",
            api_base_url=api_base_url,
        )
    return gated
