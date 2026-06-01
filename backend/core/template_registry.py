"""
Registre template-first — source de vérité des gabarits CyberForge.

Le LLM ne choisit pas la structure HTML : il remplit des slots dans un template validé.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from core.agent_contract import AgentContractError

RenderKind = Literal["vitrine_shell", "html_seed", "next_scaffold", "react_scaffold", "llm_only"]


@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    label: str
    render_kind: RenderKind
    project_types: frozenset[str]
    generation_modes: frozenset[str]
    required_slots: frozenset[str]
    description: str = ""


# Catalogue non négociable — tout nouveau type passe par ici.
TEMPLATE_CATALOG: dict[str, TemplateDefinition] = {
    "landing": TemplateDefinition(
        id="landing",
        label="Landing page",
        render_kind="vitrine_shell",
        project_types=frozenset({"site_web", "landing_page"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name", "sector", "city"}),
        description="Vitrine HTML premium (navbar, hero, services, contact).",
    ),
    "taskflow": TemplateDefinition(
        id="taskflow",
        label="TaskFlow",
        render_kind="html_seed",
        project_types=frozenset({"saas_dashboard", "application_web", "projet_generique"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name"}),
        description="Démo SaaS gestion de tâches — template Python.",
    ),
    "crm": TemplateDefinition(
        id="crm",
        label="CRM",
        render_kind="html_seed",
        project_types=frozenset({"application_web", "saas_dashboard"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name"}),
    ),
    "dashboard": TemplateDefinition(
        id="dashboard",
        label="Dashboard analytics",
        render_kind="html_seed",
        project_types=frozenset({"saas_dashboard", "application_web"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name"}),
    ),
    "facturation": TemplateDefinition(
        id="facturation",
        label="Facturation",
        render_kind="html_seed",
        project_types=frozenset({"application_web"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name"}),
    ),
    "reservation": TemplateDefinition(
        id="reservation",
        label="Réservations",
        render_kind="html_seed",
        project_types=frozenset({"site_web", "application_web"}),
        generation_modes=frozenset({"client_demo"}),
        required_slots=frozenset({"brand_name"}),
    ),
    "vitrine_next": TemplateDefinition(
        id="vitrine_next",
        label="Vitrine Next.js",
        render_kind="next_scaffold",
        project_types=frozenset({"site_web", "landing_page"}),
        generation_modes=frozenset({"vitrine_next"}),
        required_slots=frozenset({"brand_name"}),
    ),
    "real_app": TemplateDefinition(
        id="real_app",
        label="Application React",
        render_kind="react_scaffold",
        project_types=frozenset({"application_web", "application_mobile"}),
        generation_modes=frozenset({"real_app"}),
        required_slots=frozenset(),
        description="Génération LLM autorisée (hors template HTML fixe).",
    ),
}


def normalize_template_id(template_id: str) -> str:
    tid = (template_id or "").strip().lower()
    if tid == "invoice":
        return "facturation"
    return tid


def get_template(template_id: str) -> TemplateDefinition | None:
    return TEMPLATE_CATALOG.get(normalize_template_id(template_id))


def require_template_for_plan(
    *,
    template_id: str,
    project_type: str,
    generation_mode: str,
) -> TemplateDefinition:
    """Lève AgentContractError si le template ArchitectAI est absent ou incompatible."""
    tid = normalize_template_id(template_id)
    definition = get_template(tid)
    if definition is None:
        raise AgentContractError(
            agent_id="architect",
            code="unknown_template",
            message=f"Template « {template_id} » absent du catalogue template-first.",
            detail=f"Catalogue : {', '.join(sorted(TEMPLATE_CATALOG))}",
        )
    pt = (project_type or "").strip().lower()
    mode = (generation_mode or "client_demo").strip().lower()
    if definition.project_types and pt not in definition.project_types:
        raise AgentContractError(
            agent_id="architect",
            code="template_project_mismatch",
            message=(
                f"Template « {tid} » incompatible avec le type projet « {pt} »."
            ),
        )
    if definition.generation_modes and mode not in definition.generation_modes:
        raise AgentContractError(
            agent_id="architect",
            code="template_mode_mismatch",
            message=(
                f"Template « {tid} » incompatible avec generation_mode « {mode} »."
            ),
        )
    return definition


def list_templates_for_mode(generation_mode: str) -> list[TemplateDefinition]:
    mode = (generation_mode or "client_demo").strip().lower()
    return [
        t
        for t in TEMPLATE_CATALOG.values()
        if mode in t.generation_modes
    ]


def is_template_first_mode(generation_mode: str | None, *, render_kind: RenderKind | None = None) -> bool:
    """True si le pipeline doit passer par le moteur template (pas HTML LLM libre)."""
    mode = (generation_mode or "client_demo").strip().lower()
    if mode in ("real_app",):
        return False
    if mode == "vitrine_next":
        return True
    if render_kind:
        return render_kind in ("vitrine_shell", "html_seed", "next_scaffold")
    return mode == "client_demo"
