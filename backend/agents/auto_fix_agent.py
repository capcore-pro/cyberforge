"""
AutoFixAI — corrige les livrables HTML défectueux (régénération vanilla, repli TaskFlow).
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


class AutoFixAgent(BaseAgent):
    """
    Relance la génération HTML vanilla si BugHunter signale des défauts.
    Après MAX_FIX_ATTEMPTS échecs, applique le template TaskFlow premium.
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

    async def repair(
        self,
        *,
        user_prompt: str,
        tier: CodeGenComplexity,
        title: str,
        initial_report: BugHuntReport,
    ) -> tuple[CodeGenerateResult, int, BugHuntReport]:
        """
        Tente jusqu'à MAX_FIX_ATTEMPTS régénérations, puis repli TaskFlow.

        Retourne (generation finale, nombre de tentatives effectuées, dernier rapport).
        """
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
        fallback_html = build_task_manager_standalone_html(
            title=title,
            subtitle="Démo interactive — interface TaskFlow (repli qualité).",
            sources=user_prompt[:8000],
        )
        fallback_report = hunter.analyze_html(fallback_html)
        return (
            code_result_from_html(
                fallback_html,
                summary=(
                    "Template TaskFlow premium appliqué après échec des corrections "
                    f"({MAX_FIX_ATTEMPTS} tentatives)."
                ),
                model=TASKFLOW_FALLBACK_MODEL,
                provider=TASKFLOW_FALLBACK_PROVIDER,
            ),
            MAX_FIX_ATTEMPTS,
            fallback_report,
        )

    async def run(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError(
            "AutoFixAI s'utilise via repair() dans le pipeline CoreMind."
        )
