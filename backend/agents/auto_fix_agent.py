"""
AutoFixAI — corrige les livrables HTML défectueux.
Repli aligné sur le template ArchitectAI (TaskFlow uniquement pour SaaS explicite).
"""

from __future__ import annotations

import logging
from typing import Any

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.builder_agent import BuilderAgent
from agents.bug_hunter_agent import BugHuntReport, BugHunterAgent
from agents.coremind_agent import CoreMindAnalysis
from agents.demo_quality import code_result_from_html, preview_html_from_generation
from agents.vitrine_policy import is_vitrine_html_project
from prompts import build_autofix_prompt
from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    CodeGenerateResult,
)
from tools.demo_template_service import TEMPLATE_LABELS, TEMPLATE_TASKFLOW
from tools.template_fallback import (
    TEMPLATE_FALLBACK_MODEL,
    TEMPLATE_FALLBACK_PROVIDER,
    build_template_fallback_html,
)

logger = logging.getLogger(__name__)

MAX_FIX_ATTEMPTS = 3

_IMMEDIATE_FALLBACK_CODES = frozenset(
    {"visible_source", "broken_js", "render_error", "empty_elements"}
)


def needs_immediate_template_fallback(report: BugHuntReport) -> bool:
    """True si le livrable ne doit pas passer par des régénérations LLM."""
    return bool(_IMMEDIATE_FALLBACK_CODES.intersection(report.issue_codes))


# Rétrocompat tests v1
needs_immediate_taskflow_fallback = needs_immediate_template_fallback


class AutoFixAgent(BaseAgent):
    """
    Régénère via LLM puis repli template premium (ArchitectAI).
    Vitrines : reprise BuilderAI simplifiée.
    """

    @property
    def agent_id(self) -> str:
        return "autofix"

    @property
    def name(self) -> str:
        return "AutoFixAI"

    def _build_fix_prompt(
        self,
        user_prompt: str,
        report: BugHuntReport,
        attempt: int,
    ) -> str:
        issues_text = "\n".join(
            f"- [{issue.code}] {issue.message}" for issue in report.issues[:12]
        ) or "- Qualité HTML insuffisante."
        return build_autofix_prompt(
            user_prompt,
            issues_text=issues_text,
            attempt=attempt,
            max_attempts=MAX_FIX_ATTEMPTS,
        )

    def _apply_template_fallback(
        self,
        *,
        user_prompt: str,
        title: str,
        attempts: int,
        reason: str,
        plan: ArchitectPlan | None = None,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        hunter = BugHunterAgent(self._settings)
        template_id = plan.template if plan else TEMPLATE_TASKFLOW
        fallback_html, resolved_template = build_template_fallback_html(
            user_prompt=user_prompt,
            title=title,
            template=template_id,
        )
        fallback_report = hunter.analyze_html(fallback_html)
        label = TEMPLATE_LABELS.get(resolved_template, resolved_template)
        logger.info(
            "[AutoFixAI] repli template %s | reason=%s | attempts=%s | ok=%s",
            resolved_template,
            reason,
            attempts,
            fallback_report.ok,
        )
        return (
            code_result_from_html(
                fallback_html,
                summary=f"Template {label} premium ({reason}).",
                model=TEMPLATE_FALLBACK_MODEL,
                provider=TEMPLATE_FALLBACK_PROVIDER,
            ),
            attempts,
            fallback_report,
        )

    async def _apply_vitrine_builder_retry(
        self,
        *,
        user_prompt: str,
        title: str,
        attempts: int,
        reason: str,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        project_id: str | None = None,
        generation_mode: str | None = None,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        del generation_mode
        builder = BuilderAgent(self._settings)
        generation, preview_html = await builder.build_simplified_vitrine_retry(
            user_prompt,
            plan=plan,
            analysis=analysis,
            settings=self._settings,
            project_id=project_id,
        )
        html = preview_html or generation.code or ""
        hunter = BugHunterAgent(self._settings)
        report = hunter.analyze_html(html)
        logger.info(
            "[AutoFixAI] reprise vitrine BuilderAI | reason=%s | attempts=%s | ok=%s",
            reason,
            attempts,
            report.ok,
        )
        summary = f"Reprise vitrine BuilderAI ({reason})."
        if generation.summary and "TaskFlow" not in generation.summary:
            summary = generation.summary
        return (
            code_result_from_html(
                html,
                summary=summary,
                model=generation.model,
                provider=generation.provider,
            ),
            attempts,
            report,
        )

    async def _resolve_fallback(
        self,
        *,
        user_prompt: str,
        title: str,
        attempts: int,
        reason: str,
        plan: ArchitectPlan | None,
        analysis: CoreMindAnalysis | None,
        project_id: str | None,
        generation_mode: str | None,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        if (
            plan is not None
            and analysis is not None
            and is_vitrine_html_project(plan, generation_mode=generation_mode)
        ):
            return await self._apply_vitrine_builder_retry(
                user_prompt=user_prompt,
                title=title,
                attempts=attempts,
                reason=reason,
                plan=plan,
                analysis=analysis,
                project_id=project_id,
                generation_mode=generation_mode,
            )
        return self._apply_template_fallback(
            user_prompt=user_prompt,
            title=title,
            attempts=attempts,
            reason=reason,
            plan=plan,
        )

    async def repair(
        self,
        *,
        user_prompt: str,
        tier: CodeGenComplexity,
        title: str,
        initial_report: BugHuntReport,
        project_id: str | None = None,
        plan: ArchitectPlan | None = None,
        analysis: CoreMindAnalysis | None = None,
        generation_mode: str | None = None,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        """
        Régénération LLM puis repli template ArchitectAI si échec.
        Vitrines : reprise BuilderAI simplifiée.
        """
        if needs_immediate_template_fallback(initial_report):
            logger.info(
                "[AutoFixAI] repli immédiat | issues=%s | vitrine=%s",
                initial_report.issue_codes,
                plan is not None
                and is_vitrine_html_project(plan, generation_mode=generation_mode),
            )
            return await self._resolve_fallback(
                user_prompt=user_prompt,
                title=title,
                attempts=0,
                reason="code source ou rendu cassé détecté",
                plan=plan,
                analysis=analysis,
                project_id=project_id,
                generation_mode=generation_mode,
            )

        codegen = CodeGenService(self._settings)
        hunter = BugHunterAgent(self._settings)
        last_report = initial_report

        for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
            fix_prompt = self._build_fix_prompt(user_prompt, last_report, attempt)
            logger.info(
                "[AutoFixAI] tentative %s/%s | issues=%s",
                attempt,
                MAX_FIX_ATTEMPTS,
                last_report.issue_codes,
            )
            try:
                generation = await codegen.generate_code(
                    fix_prompt,
                    tier,
                    demo_html=True,
                    project_id=project_id,
                )
            except Exception:
                logger.exception("[AutoFixAI] échec appel LLM tentative %s", attempt)
                continue

            html = preview_html_from_generation(generation, title=title)
            last_report = hunter.analyze_html(html)
            if needs_immediate_template_fallback(last_report):
                return await self._resolve_fallback(
                    user_prompt=user_prompt,
                    title=title,
                    attempts=attempt,
                    reason="régénération encore défectueuse",
                    plan=plan,
                    analysis=analysis,
                    project_id=project_id,
                    generation_mode=generation_mode,
                )
            if last_report.ok:
                logger.info("[AutoFixAI] HTML validé après tentative %s", attempt)
                return (
                    code_result_from_html(
                        html,
                        summary=(
                            f"{generation.summary} (corrigé par AutoFixAI, "
                            f"tentative {attempt})"
                        ),
                        model=generation.model,
                        provider=generation.provider,
                    ),
                    attempt,
                    last_report,
                )

        logger.warning(
            "[AutoFixAI] échec après %s tentatives — repli template ArchitectAI",
            MAX_FIX_ATTEMPTS,
        )
        return await self._resolve_fallback(
            user_prompt=user_prompt,
            title=title,
            attempts=MAX_FIX_ATTEMPTS,
            reason=f"échec après {MAX_FIX_ATTEMPTS} tentatives",
            plan=plan,
            analysis=analysis,
            project_id=project_id,
            generation_mode=generation_mode,
        )

    async def run(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError(
            "AutoFixAI s'utilise via repair() dans le pipeline CoreMind."
        )
