"""
Pipeline Graph — CyberForge (OpenHands)
Orchestre la boucle OpenHands entre GeneratorAI et SupervisorAI.
Synchronisé avec SharedContext — même session que tous les autres agents.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.openhands_agent import normalize_project_type, openhands_agent
from agents.shared_context import SharedContext

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
QUALITY_THRESHOLD = 70  # score minimum pour passer à SupervisorAI


def _extract_code(shared_context: dict[str, Any]) -> str:
    return str(
        shared_context.get("generated_html")
        or shared_context.get("generated_code")
        or ""
    )


def _write_code(shared_context: dict[str, Any], code: str) -> None:
    if shared_context.get("generated_html") is not None or "generated_html" in shared_context:
        shared_context["generated_html"] = code
    if shared_context.get("generated_code") is not None or "generated_code" in shared_context:
        shared_context["generated_code"] = code
    if "generated_html" not in shared_context and "generated_code" not in shared_context:
        shared_context["generated_html"] = code


async def run_openhands_pipeline(
    shared_context: dict[str, Any],
    project_type: str,
    project_name: str = "",
) -> dict[str, Any]:
    """
    Boucle principale OpenHands.
    Reçoit le code depuis SharedContext après GeneratorAI.
    Retourne le SharedContext mis à jour avec le code corrigé.
    """
    if shared_context.get("openhands_enabled") is False:
        shared_context["openhands_status"] = "skipped"
        return shared_context

    code = _extract_code(shared_context)
    if not code:
        logger.warning("OpenHands: aucun code trouvé dans SharedContext — skipped")
        shared_context["openhands_status"] = "skipped"
        return shared_context

    ctx = SharedContext.from_dict(shared_context)
    max_iterations = max(1, int(ctx.openhands_max_iterations or MAX_ITERATIONS))

    shared_context["openhands_status"] = "analyzing"
    shared_context["openhands_iterations"] = 0
    shared_context["openhands_issues_found"] = []
    shared_context["openhands_corrections_applied"] = []
    shared_context.setdefault("openhands_quality_before", 0.0)

    current_code = code
    all_issues: list[Any] = []
    all_corrections: list[Any] = []
    quality_score = 0.0
    result: dict[str, Any] = {}

    for iteration in range(1, max_iterations + 1):
        logger.info(
            "OpenHands — itération %s/%s — projet: %s",
            iteration,
            max_iterations,
            project_name,
        )

        shared_context["openhands_status"] = f"analyzing_iteration_{iteration}"
        shared_context["openhands_iterations"] = iteration

        result = await openhands_agent.analyze_and_fix(
            current_code,
            normalize_project_type(project_type),
            project_name=project_name,
            iteration=iteration,
        )

        issues = list(result.get("issues_found") or [])
        corrections = list(result.get("corrections_applied") or [])
        corrected_code = str(result.get("corrected_code") or current_code)
        quality_score = float(result.get("quality_score") or 75)

        if iteration == 1 and not shared_context.get("openhands_quality_before"):
            shared_context["openhands_quality_before"] = quality_score

        all_issues.extend(issues)
        all_corrections.extend(corrections)
        current_code = corrected_code

        logger.info(
            "OpenHands itération %s — %s issues — score: %s",
            iteration,
            len(issues),
            quality_score,
        )

        if not issues or quality_score >= QUALITY_THRESHOLD:
            logger.info("OpenHands — qualité atteinte après %s itération(s)", iteration)
            break

    _write_code(shared_context, current_code)

    shared_context["openhands_status"] = "done"
    shared_context["openhands_issues_found"] = all_issues
    shared_context["openhands_corrections_applied"] = all_corrections
    shared_context["openhands_quality_after"] = quality_score
    shared_context["openhands_report"] = {
        "iterations": shared_context["openhands_iterations"],
        "total_issues_found": len(all_issues),
        "total_corrections_applied": len(all_corrections),
        "issues": all_issues,
        "corrections": all_corrections,
        "quality_score_final": quality_score,
        "source": result.get("source", "unknown"),
    }

    logger.info(
        "OpenHands terminé — %s issues corrigées en %s itération(s)",
        len(all_issues),
        shared_context["openhands_iterations"],
    )

    return shared_context


async def run_debug_pipeline(
    code: str,
    project_type: str,
    project_name: str = "",
) -> dict[str, Any]:
    """
    Mode Debug — déclenché manuellement depuis l'interface projet.
    Retourne directement le rapport + code corrigé sans passer par SharedContext.
    """
    shared_context: dict[str, Any] = {
        "generated_html": code,
        "generated_code": code,
        "openhands_enabled": True,
    }

    result = await run_openhands_pipeline(
        shared_context=shared_context,
        project_type=project_type,
        project_name=project_name,
    )

    return {
        "corrected_code": _extract_code(result) or code,
        "report": result.get("openhands_report", {}),
        "status": result.get("openhands_status", "done"),
        "iterations": result.get("openhands_iterations", 0),
    }
