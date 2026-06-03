"""
Moteur de rendu template-first — assemble HTML à partir du catalogue, pas du LLM.
"""

from __future__ import annotations

import html as html_lib
import logging
from typing import Any

from agents.architect_agent import ArchitectPlan
from agents.demo_quality import code_result_from_html
from core.agent_contract import AgentContractError, AgentResult
from core.template_registry import TemplateDefinition
from tools.client_content_profile import (
    ClientContentProfile,
    build_client_content_profile,
    format_client_page_title,
    format_client_tagline,
)
from tools.codegen_service import CodeGenerateResult
from tools.demo_pipeline import build_client_demo_document
from tools.demo_template_service import TEMPLATE_MODEL, TEMPLATE_PROVIDER
from agents.design_system_ai import inject_design_system_into_html
from tools.vitrine_html_enhance import enhance_builder_vitrine_html

logger = logging.getLogger(__name__)


def _validate_profile_slots(
    profile: ClientContentProfile,
    definition: TemplateDefinition,
) -> None:
    missing: list[str] = []
    if "brand_name" in definition.required_slots and not profile.company_name:
        missing.append("brand_name")
    if "sector" in definition.required_slots and not profile.sector:
        missing.append("sector")
    if "city" in definition.required_slots and not profile.city:
        missing.append("city")
    if missing:
        raise AgentContractError(
            agent_id="template_engine",
            code="missing_slots",
            message=f"Slots obligatoires manquants : {', '.join(missing)}",
            detail="Complétez ResearchAI ou le prompt (nom, secteur, ville).",
        )


def _build_vitrine_body_html(
    profile: ClientContentProfile,
    *,
    user_prompt: str,
    research_brief: Any | None,
) -> str:
    """Corps HTML minimal injecté dans le shell premium (pas de génération structurelle LLM)."""
    brand = html_lib.escape(profile.display_name)
    tagline = html_lib.escape(format_client_tagline(profile, user_prompt=user_prompt))
    city = html_lib.escape(profile.city or "")
    sector = html_lib.escape(profile.sector_label_for(user_prompt) or profile.sector or "")

    services_html = ""
    for label_raw in ("Nos prestations", "Accompagnement", "Qualité de service"):
        label = html_lib.escape(label_raw)
        services_html += (
            f'<article class="cf-vitrine-card"><h3>{label}</h3>'
            f"<p>{tagline}</p></article>"
        )
    if not services_html:
        services_html = (
            f'<article class="cf-vitrine-card"><h3>Nos spécialités</h3>'
            f"<p>Découvrez l'expertise {brand}.</p></article>"
            f'<article class="cf-vitrine-card"><h3>Qualité</h3>'
            f"<p>Service {sector} à {city or 'votre région'}.</p></article>"
        )

    return f"""
<section id="services" class="cf-vitrine-section">
  <h2>Nos services</h2>
  <div class="cf-vitrine-cards">{services_html}</div>
</section>
<section id="about" class="cf-vitrine-section">
  <h2>À propos</h2>
  <p>{brand} est votre référence {sector.lower()} {f"à {city}" if city else ""}. {tagline}.</p>
</section>
<section id="contact" class="cf-vitrine-section">
  <h2>Contact</h2>
  <p>Contactez {brand} pour un devis ou une visite.</p>
  <form id="cf-contact-form" action="#" method="post" onsubmit="return false;">
    <label>Nom <input type="text" name="name" required /></label>
    <label>Email <input type="email" name="email" required /></label>
    <label>Message <textarea name="message" required></textarea></label>
    <button type="submit" class="cf-btn-primary">Envoyer à {brand}</button>
  </form>
</section>
"""


async def render_template(
    definition: TemplateDefinition,
    *,
    plan: ArchitectPlan,
    user_prompt: str,
    research_brief: Any | None = None,
    project_id: str | None = None,
    design_system: Any | None = None,
    sector_template_html: str | None = None,
) -> AgentResult[tuple[CodeGenerateResult, str]]:
    """
    Rend le livrable pour un template du catalogue.
    Retourne (generation, preview_html) ou échec explicite.
    """
    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_brief,
        plan=plan,
    )
    try:
        _validate_profile_slots(profile, definition)
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id="template_engine",
            agent_name="TemplateEngine",
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )

    kind = definition.render_kind
    try:
        if kind == "vitrine_shell":
            if sector_template_html and len(sector_template_html.strip()) > 500:
                preview = sector_template_html
                from tools.client_content_profile import repair_client_literals_in_html

                preview = repair_client_literals_in_html(
                    preview,
                    profile=profile,
                    user_prompt=user_prompt,
                )
            else:
                body = _build_vitrine_body_html(
                    profile,
                    user_prompt=user_prompt,
                    research_brief=research_brief,
                )
                draft = (
                    f"<!DOCTYPE html><html lang='fr'><head>"
                    f"<meta charset='UTF-8'/>"
                    f"<title>{html_lib.escape(format_client_page_title(profile, user_prompt=user_prompt))}</title>"
                    f"</head><body>{body}</body></html>"
                )
                preview = enhance_builder_vitrine_html(
                    draft,
                    plan=plan,
                    research_brief=research_brief,
                    user_prompt=user_prompt,
                )
            if design_system:
                preview = inject_design_system_into_html(preview, design_system)
            generation = code_result_from_html(
                preview,
                summary=f"Vitrine template-first — {definition.label}",
                model=TEMPLATE_MODEL,
                provider="template_first",
            )
            return AgentResult.success(
                agent_id="template_engine",
                agent_name="TemplateEngine",
                data=(generation, preview),
                meta={"template_id": definition.id, "render_kind": kind},
            )

        if kind == "html_seed":
            enriched = (
                f"Type : {plan.project_type_label}.\n"
                f"Template : {definition.label} ({definition.id}).\n\n"
                f"{user_prompt.strip()}"
            )
            document = await build_client_demo_document(
                enriched,
                project_type_label=plan.project_type_label,
                project_id=project_id,
                template_hint=definition.id,
            )
            if document.template != definition.id:
                logger.warning(
                    "[TemplateEngine] template demandé=%s rendu=%s",
                    definition.id,
                    document.template,
                )
            preview = document.html
            if design_system:
                preview = inject_design_system_into_html(preview, design_system)
            generation = document.generation
            generation = CodeGenerateResult(
                summary=generation.summary or f"Démo {definition.label} (template-first)",
                code=preview,
                files=generation.files,
                stack=generation.stack,
                model=TEMPLATE_MODEL,
                provider="template_first",
                demo_seed=generation.demo_seed,
            )
            return AgentResult.success(
                agent_id="template_engine",
                agent_name="TemplateEngine",
                data=(generation, preview),
                meta={"template_id": document.template, "render_kind": kind},
            )

        return AgentResult.failure(
            agent_id="template_engine",
            agent_name="TemplateEngine",
            code="unsupported_render_kind",
            message=f"Rendu non implémenté pour render_kind={kind!r}.",
            detail="Utilisez le pipeline dédié (vitrine_next / real_app).",
        )
    except AgentContractError:
        raise
    except Exception as exc:
        logger.exception("[TemplateEngine] échec rendu template %s", definition.id)
        return AgentResult.failure(
            agent_id="template_engine",
            agent_name="TemplateEngine",
            code="render_failed",
            message=f"Échec du rendu template « {definition.id} ».",
            detail=str(exc),
        )
