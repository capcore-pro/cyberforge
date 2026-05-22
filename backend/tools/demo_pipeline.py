"""
Pipeline unique démo client — TaskFlow premium + seed → un seul index.html.

Point d'entrée pour CoreMind, POST /demos, aperçu local et Cloudflare.
Pas de génération HTML par LLM, pas de conversion JSX, pas de BugHunter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import Settings, get_settings
from tools.codegen_service import CodeGenerateResult
from tools.demo_template_service import (
    DemoSeedData,
    DemoTemplateService,
    build_html_from_seed,
    seed_as_dict,
    seed_from_dict,
    seed_to_code_result,
)
from tools.standalone_demo_html import wrap_with_password_gate

logger = logging.getLogger(__name__)

PIPELINE_TEMPLATE = "taskflow"
INDEX_HTML_PATH = "index.html"


@dataclass(frozen=True)
class ClientDemoDocument:
    """
    Livrable démo unique.

    html : document TaskFlow plain (sans gate) — aperçu local + base Cloudflare.
    """

    html: str
    seed: DemoSeedData
    generation: CodeGenerateResult

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
    Produit le HTML final TaskFlow à partir du prompt (seed LLM ou heuristique).
    """
    svc = DemoTemplateService(settings)
    resolved = seed or await svc.resolve_seed(
        user_prompt.strip(),
        project_type_label=project_type_label,
    )
    html = build_html_from_seed(resolved)
    if "saas-shell" not in html or len(html) < 1000:
        raise ValueError("Pipeline démo : HTML TaskFlow invalide.")

    summary = (
        f"Démo {resolved.brand_name} — TaskFlow premium"
        + (" (seed IA)" if resolved.llm_personalized else " (seed locale)")
    )
    generation = seed_to_code_result(resolved, summary=summary + ".")

    logger.info(
        "[DemoPipeline] document prêt | brand=%s | tasks=%s | bytes=%s | seed_ia=%s",
        resolved.brand_name,
        len(resolved.tasks),
        len(html.encode("utf-8")),
        resolved.llm_personalized,
    )
    return ClientDemoDocument(html=html, seed=resolved, generation=generation)


def client_demo_from_seed_dict(data: dict[str, object]) -> ClientDemoDocument:
    """Reconstruit le document à partir d'une seed sérialisée (POST /demos)."""
    resolved = seed_from_dict(data)
    html = build_html_from_seed(resolved)
    generation = seed_to_code_result(
        resolved,
        summary=f"Démo {resolved.brand_name} — TaskFlow premium.",
    )
    return ClientDemoDocument(html=html, seed=resolved, generation=generation)


def wrap_demo_for_cloudflare(
    document: ClientDemoDocument,
    password: str,
    *,
    title: str = "Démo CyberForge",
) -> str:
    """Applique le gate mot de passe pour le déploiement Pages / unlock local."""
    gated = wrap_with_password_gate(document.html, password.strip(), title=title)
    if "cf-password-toggle" not in gated:
        raise ValueError("Gate mot de passe invalide (cf-password-toggle manquant).")
    return gated
