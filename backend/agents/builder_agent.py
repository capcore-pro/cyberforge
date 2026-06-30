"""
BuilderAI ΓÇö v2 assemblage template (vitrines) ou v0/DeepSeek (apps m├⌐tier).

D├⌐l├¿gue l'assemblage HTML ├á builder_ai.py ΓÇö ne g├⌐n├¿re plus de vitrine from scratch.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.builder_ai import (
    append_design_system_to_prompt,
    assemble_template_html,
    resolve_assembly_inputs,
    uses_llm_with_design_system,
    uses_template_assembly,
)
from agents.coremind_agent import (
    ComplexityLevel,
    CoreMindAnalysis,
    ProjectType,
    RecommendedTool,
)
from agents.demo_quality import code_result_from_html, preview_html_from_generation
from config import Settings
from agents.content_ai import inject_stripe
from agents.design_system_ai import apply_design_system_to_html
from tools.builder_generators import (
    BuildOutcome,
    DeepSeekBuilderClient,
    V0Client,
)
from tools.codegen_service import CodeGenComplexity, CodeGenService, CodeGenerateResult
from tools.toolbox_branding import apply_toolbox_to_generation, build_toolbox_builder_context
from prompts import (
    BUILDER_VITRINE_HTML_DIRECTIVE,
    PERSONALIZED_CONTENT_DIRECTIVE,
    SIMPLIFIED_VITRINE_DIRECTIVE,
)
from agents.research_agent import ResearchBrief, format_research_brief_for_prompt
from agents.vitrine_policy import is_vitrine_html_project
from tools.client_content_profile import (
    build_client_content_profile,
    format_literal_client_directive,
    log_client_content_context,
)
from tools.cms_panel_inject import CMS_BUILDER_HINT
from core.agent_contract import require_ok

logger = logging.getLogger(__name__)

# Cat├⌐gories template-first : si sector_template_html est dans le state ΓåÆ assemblage obligatoire.
_FORCED_ASSEMBLY_PRICING_CATEGORIES = frozenset(
    {
        "ecommerce",
        "site_reservation",
        "application_web",
        "application_desktop",
    }
)


def must_force_sector_template_assembly(
    plan: ArchitectPlan,
    *,
    sector_template_html: str | None,
    sector_template: dict[str, Any] | None,
) -> bool:
    """
    True si le pipeline a d├⌐j├á un template sectoriel et qu'on ne doit jamais
    retomber sur CoreMind / v0 (ecommerce, r├⌐servation, app, desktop).
    """
    category = (getattr(plan, "pricing_category", None) or "").strip().lower()
    pt = plan.project_type.value if hasattr(plan.project_type, "value") else str(
        plan.project_type
    )
    category_ok = category in _FORCED_ASSEMBLY_PRICING_CATEGORIES or pt == "saas_dashboard"
    if not category_ok:
        return False

    html = (sector_template_html or "").strip()
    if len(html) >= 200:
        return True
    if isinstance(sector_template, dict):
        for key in ("html", "html_raw"):
            chunk = sector_template.get(key)
            if isinstance(chunk, str) and len(chunk.strip()) >= 200:
                return True
    return False


_UI_KEYWORDS = re.compile(
    r"\b(react|next\.?js|nextjs|jsx|tsx|tailwind|shadcn|ui|interface|"
    r"composant|component|landing|dashboard|design)\b",
    re.IGNORECASE,
)
_BACKEND_COMPLEX_KEYWORDS = re.compile(
    r"\b(api|backend|rest|graphql|fastapi|microservice|database|"
    r"postgresql|auth|oauth|stripe|webhook|websocket|kubernetes)\b",
    re.IGNORECASE,
)


class BuilderProvider(str, Enum):
    V0 = "v0"
    DEEPSEEK = "deepseek"
    ASSEMBLY = "assembly"


class BuilderDecision(BaseModel):
    """D├⌐cision de routage BuilderAI (align├⌐e sur CoreMindAI)."""

    provider: BuilderProvider
    rationale: str


class BuilderRunResult(BaseModel):
    """R├⌐sultat d'ex├⌐cution BuilderAI."""

    agent_id: str = "builder"
    agent_name: str = "BuilderAI"
    decision: BuilderDecision
    outcome: BuildOutcome | None = None
    fallback_to_coremind: bool = True
    generation: CodeGenerateResult | None = None
    preview_html: str | None = None


class BuilderAgent(BaseAgent):
    """Assemble les vitrines depuis template ; v0/DeepSeek pour apps m├⌐tier."""

    @property
    def agent_id(self) -> str:
        return "builder"

    @property
    def name(self) -> str:
        return "BuilderAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        plan = kwargs.get("architect_plan")
        analysis = kwargs.get("analysis")
        if not isinstance(plan, ArchitectPlan) or not isinstance(analysis, CoreMindAnalysis):
            raise ValueError("architect_plan et analysis requis pour BuilderAI")
        result = await self.build(prompt, plan=plan, analysis=analysis, **kwargs)
        return result.model_dump_json()

    def select_provider(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
    ) -> BuilderDecision:
        text = f"{prompt}\n{plan.project_type_label}\n{plan.template}"

        if analysis.recommended_tool == RecommendedTool.DEEPSEEK:
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale=analysis.tool_rationale
                or "CoreMindAI ΓÇö logique backend / complexit├⌐ ├⌐lev├⌐e ΓåÆ DeepSeek.",
            )

        if _BACKEND_COMPLEX_KEYWORDS.search(text) or plan.project_type in (
            ProjectType.API_BACKEND,
            ProjectType.EXTENSION_NAVIGATEUR,
            ProjectType.APPLICATION_MOBILE,
            ProjectType.APPLICATION_DESKTOP,
        ):
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale="Backend ou logique complexe d├⌐tect├⌐e ΓÇö DeepSeek.",
            )

        if analysis.recommended_tool == RecommendedTool.V0:
            return BuilderDecision(
                provider=BuilderProvider.V0,
                rationale=analysis.tool_rationale
                or "CoreMindAI ΓÇö interface React ΓåÆ v0.",
            )

        if analysis.complexity == ComplexityLevel.ELEVEE and not _UI_KEYWORDS.search(text):
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale="Complexit├⌐ ├⌐lev├⌐e sans focus UI ΓÇö DeepSeek.",
            )

        if _UI_KEYWORDS.search(text) or plan.project_type in (
            ProjectType.APPLICATION_WEB,
            ProjectType.LANDING_PAGE,
            ProjectType.SITE_WEB,
            ProjectType.SAAS_DASHBOARD,
        ):
            return BuilderDecision(
                provider=BuilderProvider.V0,
                rationale="Stack UI React/Next.js ΓÇö v0 by Vercel.",
            )

        return BuilderDecision(
            provider=BuilderProvider.V0,
            rationale="G├⌐n├⌐ration UI par d├⌐faut ΓÇö v0.",
        )

    async def build(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        settings: Settings | None = None,
        project_id: str | None = None,
        research_brief: ResearchBrief | Any | None = None,
        generation_mode: str | None = None,
        design_system: Any | None = None,
        sector_template_html: str | None = None,
        sector_template: dict[str, Any] | None = None,
        payment_config: Any | None = None,
    ) -> BuilderRunResult:
        """
        Vitrine (vitrine_next / client_demo) : assemblage template + ContentAI.
        Apps m├⌐tier : v0/DeepSeek avec design_system inject├⌐ si applicable.
        """
        del settings  # r├⌐serv├⌐ extensions

        force_assembly = must_force_sector_template_assembly(
            plan,
            sector_template_html=sector_template_html,
            sector_template=sector_template,
        )
        uses_assembly = uses_template_assembly(plan, generation_mode=generation_mode)
        logger.info(
            "[BuilderAI] build | project_type=%s | pricing_category=%s | generation_mode=%s | "
            "uses_template_assembly=%s | force_sector_assembly=%s | sector_html_chars=%d",
            plan.project_type.value,
            getattr(plan, "pricing_category", ""),
            generation_mode,
            uses_assembly,
            force_assembly,
            len((sector_template_html or "").strip()),
        )
        if force_assembly:
            logger.info(
                "[BuilderAI] FORCE assemble_template_html ΓÇö pas de CoreMind/v0 "
                "(sector_template_html pr├⌐sent, category=%s)",
                getattr(plan, "pricing_category", ""),
            )
            return await self._build_template_assembly(
                prompt,
                plan=plan,
                research_brief=research_brief,
                generation_mode=generation_mode,
                design_system=design_system,
                sector_template_html=sector_template_html,
                sector_template=sector_template,
                payment_config=payment_config,
                project_id=project_id,
                forbid_coremind_fallback=True,
            )

        if uses_assembly:
            return await self._build_template_assembly(
                prompt,
                plan=plan,
                research_brief=research_brief,
                generation_mode=generation_mode,
                design_system=design_system,
                sector_template_html=sector_template_html,
                sector_template=sector_template,
                payment_config=payment_config,
                project_id=project_id,
                forbid_coremind_fallback=False,
            )

        return await self._build_llm(
            prompt,
            plan=plan,
            analysis=analysis,
            project_id=project_id,
            research_brief=research_brief,
            generation_mode=generation_mode,
            design_system=design_system,
        )

    async def _build_template_assembly(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        research_brief: Any | None,
        generation_mode: str | None,
        design_system: Any | None,
        sector_template_html: str | None,
        sector_template: dict[str, Any] | None,
        payment_config: Any | None,
        project_id: str | None = None,
        forbid_coremind_fallback: bool = False,
    ) -> BuilderRunResult:
        mode = (generation_mode or "client_demo").strip().lower()
        html, client_name, sector, city, template_id, already_filled = resolve_assembly_inputs(
            user_prompt=prompt,
            plan=plan,
            research_content=research_brief,
            design_system=design_system,
            template_html=sector_template_html,
            sector_template=sector_template,
        )

        if not html:
            from agents.template_ai import load_sector_template_raw

            sector_key = sector or plan.secteur or "commerce"
            loaded = load_sector_template_raw(
                sector=sector_key,
                user_prompt=prompt,
                plan=plan,
            )
            if loaded.ok and loaded.data:
                html = loaded.data.html
                template_id = loaded.data.template_id
                already_filled = False

        if not html:
            logger.error("[BuilderAI] assemblage ΓÇö template HTML absent")
            if forbid_coremind_fallback:
                from tools.sector_template_catalog import load_sector_template_html_for_plan

                sector_key = sector or plan.secteur or "commerce"
                template_id, _fname, html = load_sector_template_html_for_plan(
                    plan, sector_key, prompt
                )
                already_filled = False
                logger.warning(
                    "[BuilderAI] rechargement catalogue %s (forbid CoreMind)",
                    template_id,
                )
            if not html:
                return BuilderRunResult(
                    decision=BuilderDecision(
                        provider=BuilderProvider.ASSEMBLY,
                        rationale="Template sectoriel manquant.",
                    ),
                    fallback_to_coremind=not forbid_coremind_fallback,
                )

        assembly = await assemble_template_html(
            template_html=html,
            client_name=client_name,
            sector=sector,
            city=city,
            research_content=research_brief,
            design_system=design_system,
            payment_config=payment_config,
            user_prompt=prompt,
            template_id=template_id,
            skip_content_fill=already_filled,
            strict_validate=True,
        )

        if not assembly.ok:
            err = assembly.error
            logger.warning(
                "[BuilderAI] assemble_template_html ├⌐chec (strict) | code=%s | %s ΓÇö retry loose=%s",
                err.code if err else "?",
                err.message if err else assembly,
                forbid_coremind_fallback,
            )
            assembly = await assemble_template_html(
                template_html=html,
                client_name=client_name,
                sector=sector,
                city=city,
                research_content=research_brief,
                design_system=design_system,
                payment_config=payment_config,
                user_prompt=prompt,
                template_id=template_id,
                skip_content_fill=already_filled,
                strict_validate=False,
            )

        if not assembly.ok:
            err = assembly.error
            logger.error(
                "[BuilderAI] assemble_template_html ├⌐chec | mode=%s | code=%s | %s",
                mode,
                err.code if err else "?",
                err.message if err else assembly,
            )
            return BuilderRunResult(
                decision=BuilderDecision(
                    provider=BuilderProvider.ASSEMBLY,
                    rationale="Assemblage template impossible.",
                ),
                fallback_to_coremind=not forbid_coremind_fallback,
            )

        data = require_ok(assembly)
        html_out = data.html
        if design_system:
            html_out = apply_design_system_to_html(
                html_out, design_system, log_prefix="BuilderAI"
            )
        if (isinstance(payment_config, dict) and payment_config) or "{{STRIPE" in html_out:
            html_out = inject_stripe(html_out, payment_config)

        from tools.vision_toolbox_enricher import enrich_html_with_toolbox

        if html_out and "<img" in html_out.lower():
            html_out, enrich_stats = await enrich_html_with_toolbox(
                html_out,
                plan=plan,
                prompt=prompt,
                settings=self._settings,
                project_id=project_id,
            )
            img_total = enrich_stats.photos_stock + enrich_stats.photos_replicate
            if img_total:
                logger.info("[VisionUI] %d images inject├⌐es", img_total)

        generation = data.generation
        if html_out != data.html and generation is not None:
            if hasattr(generation, "model_copy"):
                generation = generation.model_copy(update={"code": html_out})
            elif hasattr(generation, "code"):
                generation.code = html_out

        logger.info(
            "[BuilderAI] assemblage OK | mode=%s | template=%s | bytes=%s | valid=%s",
            mode,
            data.template_id,
            data.optimize_report.bytes_after,
            data.optimize_report.valid,
        )
        return BuilderRunResult(
            decision=BuilderDecision(
                provider=BuilderProvider.ASSEMBLY,
                rationale=(
                    f"Assemblage template-first ({data.template_id}) ΓÇö "
                    "ContentAI + optimisation HTML (BuilderAI v2)."
                ),
            ),
            outcome=None,
            fallback_to_coremind=False,
            generation=generation,
            preview_html=html_out,
        )

    async def _build_llm(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        project_id: str | None,
        research_brief: ResearchBrief | Any | None,
        generation_mode: str | None,
        design_system: Any | None,
    ) -> BuilderRunResult:
        resolved = self._settings
        decision = self.select_provider(prompt, plan=plan, analysis=analysis)

        toolbox_block = build_toolbox_builder_context(plan)
        research_in_prompt = "## Brief recherche" in prompt
        research_block = ""
        if not research_in_prompt:
            research_block = format_research_brief_for_prompt(
                research_brief if isinstance(research_brief, ResearchBrief) else None
            )

        if uses_llm_with_design_system(plan, generation_mode=generation_mode):
            prompt = append_design_system_to_prompt(prompt, design_system)

        logger.info(
            "[BuilderAI] LLM | provider=%s | design_system=%s | research=%s",
            decision.provider.value,
            bool(design_system),
            bool(research_block.strip()),
        )

        vitrine_rules = ""
        literal_block = ""
        if is_vitrine_html_project(plan, generation_mode=generation_mode):
            vitrine_rules = f"\n\n{BUILDER_VITRINE_HTML_DIRECTIVE}\n"
            profile = build_client_content_profile(
                user_prompt=prompt,
                research_brief=research_brief,
                plan=plan,
            )
            log_client_content_context(profile, prefix="BuilderAI")
            literal_block = format_literal_client_directive(profile, user_prompt=prompt)

        enriched = (
            f"Type : {plan.project_type_label}.\n"
            f"Template : {plan.template_label}.\n"
            f"Complexit├⌐ CoreMind : {analysis.complexity.value}.\n\n"
            f"{PERSONALIZED_CONTENT_DIRECTIVE}\n"
            f"{vitrine_rules}"
            f"{literal_block}"
            f"Si un brief ResearchAI (Brave / Exa) est pr├⌐sent en t├¬te du prompt, "
            f"utilise-le pour du contenu r├⌐el et localis├⌐ ΓÇö pas de donn├⌐es fictives.\n\n"
            f"{CMS_BUILDER_HINT}"
            f"{toolbox_block}"
            f"{research_block}"
            f"{prompt.strip()}"
        )

        if decision.provider == BuilderProvider.V0:
            outcome = await V0Client(resolved).generate_ui(enriched, project_id=project_id)
        else:
            outcome = await DeepSeekBuilderClient(resolved).generate_code(
                enriched,
                project_id=project_id,
            )

        if not outcome.success or outcome.generation is None:
            reason = outcome.error or "g├⌐n├⌐rateur indisponible"
            logger.info(
                "BuilderAI ΓÇö %s indisponible (%s), fallback CoreMindAI",
                decision.provider.value,
                reason,
            )
            return BuilderRunResult(
                decision=decision,
                outcome=outcome,
                fallback_to_coremind=True,
            )

        generation = apply_toolbox_to_generation(outcome.generation, plan, project_id=project_id)
        preview_html = preview_html_from_generation(
            generation,
            title=plan.project_type_label,
            user_prompt=enriched,
        )
        return BuilderRunResult(
            decision=decision,
            outcome=outcome,
            fallback_to_coremind=False,
            generation=generation,
            preview_html=preview_html,
        )

    async def build_simplified_vitrine_retry(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        settings: Settings | None = None,
        project_id: str | None = None,
        design_system: Any | None = None,
        sector_template: dict[str, Any] | None = None,
    ) -> tuple[CodeGenerateResult, str]:
        """Reprise vitrine ΓÇö assemblage template en priorit├⌐."""
        del project_id
        result = await self.build(
            f"{SIMPLIFIED_VITRINE_DIRECTIVE.strip()}\n\n{prompt.strip()}",
            plan=plan,
            analysis=analysis,
            settings=settings,
            generation_mode="client_demo",
            design_system=design_system,
            sector_template=sector_template,
        )
        if not result.fallback_to_coremind and result.generation is not None:
            html = (result.preview_html or result.generation.code or "").strip()
            return result.generation, html

        tier = CodeGenComplexity(analysis.complexity.value)
        codegen = CodeGenService(settings or self._settings)
        if codegen.is_configured():
            try:
                enriched = append_design_system_to_prompt(prompt, design_system)
                generation = await codegen.generate_code(
                    enriched,
                    tier,
                    demo_html=True,
                )
                generation = apply_toolbox_to_generation(generation, plan)
                preview_html = preview_html_from_generation(
                    generation,
                    title=plan.project_type_label,
                    user_prompt=enriched,
                )
                return generation, preview_html
            except Exception:
                logger.exception("[BuilderAI] CodeGen vitrine simplifi├⌐e ├⌐chou├⌐")

        from dataclasses import replace
        from tools.demo_template_service import (
            TEMPLATE_LANDING,
            build_html_from_seed,
            heuristic_demo_seed,
            seed_to_code_result,
        )

        seed = heuristic_demo_seed(prompt.strip(), project_type_label=plan.project_type_label)
        seed = replace(seed, template=TEMPLATE_LANDING)
        html = build_html_from_seed(seed)
        generation = seed_to_code_result(
            seed,
            summary="Template landing premium (reprise BuilderAI simplifi├⌐e).",
        )
        return generation, html
