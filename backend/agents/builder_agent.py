"""
BuilderAI — sous les ordres de CoreMindAI : v0 pour UI React, DeepSeek pour le code
complexe / backend. Si indisponible, le pipeline bascule sur CoreMindAI.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.coremind_agent import (
    ComplexityLevel,
    CoreMindAnalysis,
    ProjectType,
    RecommendedTool,
)
from agents.demo_quality import preview_html_from_generation
from config import Settings
from tools.builder_generators import (
    BuildOutcome,
    DeepSeekBuilderClient,
    V0Client,
)
from tools.codegen_service import CodeGenerateResult

logger = logging.getLogger(__name__)

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


class BuilderDecision(BaseModel):
    """Décision de routage BuilderAI (alignée sur CoreMindAI)."""

    provider: BuilderProvider
    rationale: str


class BuilderRunResult(BaseModel):
    """Résultat d'exécution BuilderAI."""

    agent_id: str = "builder"
    agent_name: str = "BuilderAI"
    decision: BuilderDecision
    outcome: BuildOutcome | None = None
    fallback_to_coremind: bool = True
    generation: CodeGenerateResult | None = None
    preview_html: str | None = None


class BuilderAgent(BaseAgent):
    """Route v0 (UI) ou DeepSeek (code complexe) selon CoreMindAI et le prompt."""

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
        result = await self.build(prompt, plan=plan, analysis=analysis)
        return result.model_dump_json()

    def select_provider(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
    ) -> BuilderDecision:
        """
        React/Next.js/UI → v0 ; code complexe / backend → DeepSeek.
        CoreMindAI (recommended_tool + complexité) prime sur les heuristiques.
        """
        text = f"{prompt}\n{plan.project_type_label}\n{plan.template}"

        if analysis.recommended_tool == RecommendedTool.DEEPSEEK:
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale=analysis.tool_rationale
                or "CoreMindAI — logique backend / complexité élevée → DeepSeek.",
            )

        if _BACKEND_COMPLEX_KEYWORDS.search(text) or plan.project_type in (
            ProjectType.API_BACKEND,
            ProjectType.EXTENSION_NAVIGATEUR,
            ProjectType.APPLICATION_MOBILE,
            ProjectType.APPLICATION_DESKTOP,
        ):
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale="Backend ou logique complexe détectée — DeepSeek.",
            )

        if analysis.recommended_tool == RecommendedTool.V0:
            return BuilderDecision(
                provider=BuilderProvider.V0,
                rationale=analysis.tool_rationale
                or "CoreMindAI — interface React → v0.",
            )

        if analysis.complexity == ComplexityLevel.ELEVEE and not _UI_KEYWORDS.search(text):
            return BuilderDecision(
                provider=BuilderProvider.DEEPSEEK,
                rationale="Complexité élevée sans focus UI — DeepSeek.",
            )

        if _UI_KEYWORDS.search(text) or plan.project_type in (
            ProjectType.APPLICATION_WEB,
            ProjectType.LANDING_PAGE,
            ProjectType.SITE_WEB,
            ProjectType.SAAS_DASHBOARD,
        ):
            return BuilderDecision(
                provider=BuilderProvider.V0,
                rationale="Stack UI React/Next.js — v0 by Vercel.",
            )

        return BuilderDecision(
            provider=BuilderProvider.V0,
            rationale="Génération UI par défaut — v0.",
        )

    async def build(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        settings: Settings | None = None,
        project_id: str | None = None,
    ) -> BuilderRunResult:
        """Tente v0 ou DeepSeek ; signale le fallback CoreMind si échec."""
        resolved = settings or self._settings
        decision = self.select_provider(prompt, plan=plan, analysis=analysis)
        enriched = (
            f"Type : {plan.project_type_label}.\n"
            f"Template : {plan.template_label}.\n"
            f"Complexité CoreMind : {analysis.complexity.value}.\n\n"
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
            reason = outcome.error or "générateur indisponible"
            logger.info(
                "BuilderAI — %s indisponible (%s), fallback CoreMindAI",
                decision.provider.value,
                reason,
            )
            return BuilderRunResult(
                decision=decision,
                outcome=outcome,
                fallback_to_coremind=True,
            )

        generation = outcome.generation
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
