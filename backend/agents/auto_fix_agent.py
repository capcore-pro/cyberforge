"""
AutoFixAI — corrige les livrables HTML défectueux (repli TaskFlow immédiat ou régénération).
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base_agent import BaseAgent
from agents.bug_hunter_agent import BugHuntReport, BugHunterAgent
from agents.demo_quality import code_result_from_html, preview_html_from_generation
from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    CodeGenerateResult,
)
from tools.standalone_demo_html import build_task_manager_standalone_html

logger = logging.getLogger(__name__)

MAX_FIX_ATTEMPTS = 3
TASKFLOW_FALLBACK_PROVIDER = "cyberforge"
TASKFLOW_FALLBACK_MODEL = "taskflow-premium"

# Repli TaskFlow immédiat (sans tentatives LLM) pour ces défauts.
_IMMEDIATE_TASKFLOW_CODES = frozenset(
    {"visible_source", "broken_js", "render_error", "empty_elements"}
)


def needs_immediate_taskflow_fallback(report: BugHuntReport) -> bool:
    """True si le livrable ne doit pas passer par des régénérations LLM."""
    return bool(_IMMEDIATE_TASKFLOW_CODES.intersection(report.issue_codes))


class AutoFixAgent(BaseAgent):
    """
    Applique TaskFlow premium dès que du code source / rendu cassé est détecté.
    Sinon, tente jusqu'à MAX_FIX_ATTEMPTS régénérations HTML vanilla.
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
        return (
            f"{user_prompt.strip()}\n\n"
            "---\n"
            f"CORRECTION BugHunterAI (tentative {attempt}/{MAX_FIX_ATTEMPTS}) :\n"
            "Le livrable précédent est REJETÉ. Regénère un index.html autonome "
            "en HTML/CSS/JS vanilla UNIQUEMENT.\n"
            "Interdictions : React, JSX, TypeScript, import/export, markdown, code visible.\n"
            "Exigences : <!DOCTYPE html>, <style> avec au moins 15 règles CSS, "
            "<body> avec contenu UI lisible, <script> vanilla fonctionnel si besoin.\n"
            "Problèmes détectés :\n"
            f"{issues_text}\n"
        )

    def _apply_taskflow_fallback(
        self,
        *,
        user_prompt: str,
        title: str,
        attempts: int,
        reason: str,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        hunter = BugHunterAgent(self._settings)
        fallback_html = build_task_manager_standalone_html(
            title=title,
            subtitle="Démo interactive — interface TaskFlow (repli qualité).",
            sources=user_prompt[:8000],
        )
        fallback_report = hunter.analyze_html(fallback_html)
        logger.info(
            "[AutoFixAI] repli TaskFlow premium | reason=%s | attempts=%s | ok=%s",
            reason,
            attempts,
            fallback_report.ok,
        )
        return (
            code_result_from_html(
                fallback_html,
                summary=f"Template TaskFlow premium ({reason}).",
                model=TASKFLOW_FALLBACK_MODEL,
                provider=TASKFLOW_FALLBACK_PROVIDER,
            ),
            attempts,
            fallback_report,
        )

    async def repair(
        self,
        *,
        user_prompt: str,
        tier: CodeGenComplexity,
        title: str,
        initial_report: BugHuntReport,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        """
        Repli TaskFlow immédiat si code source visible, sinon régénérations LLM.
        """
        if needs_immediate_taskflow_fallback(initial_report):
            logger.info(
                "[AutoFixAI] repli immédiat (sans LLM) | issues=%s",
                initial_report.issue_codes,
            )
            return self._apply_taskflow_fallback(
                user_prompt=user_prompt,
                title=title,
                attempts=0,
                reason="code source ou rendu cassé détecté",
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
                )
            except Exception:
                logger.exception("[AutoFixAI] échec appel LLM tentative %s", attempt)
                continue

            html = preview_html_from_generation(generation, title=title)
            last_report = hunter.analyze_html(html)
            if needs_immediate_taskflow_fallback(last_report):
                return self._apply_taskflow_fallback(
                    user_prompt=user_prompt,
                    title=title,
                    attempts=attempt,
                    reason="régénération encore défectueuse",
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
            "[AutoFixAI] échec après %s tentatives — repli TaskFlow premium",
            MAX_FIX_ATTEMPTS,
        )
        return self._apply_taskflow_fallback(
            user_prompt=user_prompt,
            title=title,
            attempts=MAX_FIX_ATTEMPTS,
            reason=f"échec après {MAX_FIX_ATTEMPTS} tentatives",
        )

    async def run(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError(
            "AutoFixAI s'utilise via repair() dans le pipeline CoreMind."
        )
