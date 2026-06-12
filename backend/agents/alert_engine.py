"""
Moteur de détection d'alertes automatiques.
Analyse les données existantes et crée des alertes dans Supabase si seuils dépassés.
100% déterministe — pas de LLM.
"""

from __future__ import annotations

import logging
from typing import Any

from db.agent_execution_store import get_agent_execution_store
from db.llm_usage_store import get_llm_usage_store
from db.monitoring_store import get_monitoring_store
from db.orchestration_store import get_orchestration_store
from db.supervisor_store import get_supervisor_store
from db.tool_store import get_tool_store

logger = logging.getLogger(__name__)

ALERT_RULES: dict[str, dict[str, Any]] = {
    "high_retry_rate": {
        "source": "supervisor_decisions",
        "severity": "warning",
        "title": "Taux de retry élevé",
        "message": (
            "SupervisorAI relance en moyenne {avg_attempts:.1f} fois — vérifier les prompts"
        ),
    },
    "low_pass_rate": {
        "source": "supervisor_decisions",
        "severity": "critical",
        "title": "Taux de validation bas",
        "message": (
            "Seulement {pass_rate_pct:.0f}% des validations réussissent — vérifier SupervisorAI"
        ),
        "create_incident": True,
    },
    "low_quality_score": {
        "source": "supervisor_decisions",
        "severity": "warning",
        "title": "Score qualité bas",
        "message": (
            "Score qualité moyen {avg_quality_score:.0f}/100 — revoir les prompts ou modèles"
        ),
    },
    "high_llm_cost": {
        "source": "llm_usage",
        "severity": "warning",
        "title": "Coût LLM mensuel élevé",
        "message": (
            "Coût LLM ce mois : {monthly_cost_usd:.2f} USD — surveiller la consommation"
        ),
    },
    "agent_failure_spike": {
        "source": "agent_executions",
        "severity": "critical",
        "title": "Taux d'échec agents élevé",
        "message": (
            "{failure_rate_pct:.0f}% des exécutions agents en échec "
            "({failure_count}/{total_executions})"
        ),
        "create_incident": True,
    },
    "orchestration_failures": {
        "source": "workflow_executions",
        "severity": "warning",
        "title": "Sessions orchestration en échec",
        "message": (
            "{failed} session(s) orchestration en échec sur {total} récentes"
        ),
    },
    "tool_execution_failures": {
        "source": "tool_executions",
        "severity": "warning",
        "title": "Échecs outils externes",
        "message": (
            "{failure_count} échec(s) outil sur {total} exécutions (30 j)"
        ),
    },
}


class AlertEngine:
    """Évalue les règles de monitoring et persiste les alertes."""

    def __init__(self, *, days: int = 30) -> None:
        self._days = max(1, days)

    async def collect_metrics(self) -> dict[str, Any]:
        supervisor = await get_supervisor_store().get_supervisor_stats(days=self._days)
        llm = await get_llm_usage_store().get_dashboard_llm_stats()
        agents = await get_agent_execution_store().get_stats(days=self._days)
        orch = await get_orchestration_store().get_stats()
        tool_stats = await get_tool_store().get_stats(days=self._days)

        total_agents = int(agents.get("total_executions") or 0)
        failure_agents = int(agents.get("failure_count") or 0)
        failure_rate = failure_agents / total_agents if total_agents > 0 else 0.0

        monthly_cost = float((llm.get("monthly") or {}).get("total_cost_usd") or 0)

        return {
            "avg_attempts": float(supervisor.get("avg_attempts") or 0),
            "pass_rate": float(supervisor.get("pass_rate") or 0),
            "pass_rate_pct": float(supervisor.get("pass_rate") or 0) * 100,
            "avg_quality_score": float(supervisor.get("avg_quality_score") or 0),
            "total_validations": int(supervisor.get("total_validations") or 0),
            "monthly_cost_usd": monthly_cost,
            "total_executions": total_agents,
            "failure_count": failure_agents,
            "failure_rate": failure_rate,
            "failure_rate_pct": failure_rate * 100,
            "orchestration_total": int(orch.get("total") or 0),
            "orchestration_failed": int(orch.get("failed") or 0),
            "tool_total": int(tool_stats.get("total") or 0),
            "tool_failure_count": int(tool_stats.get("failure_count") or 0),
        }

    async def scan(self) -> dict[str, Any]:
        store = get_monitoring_store()
        if not store.is_configured():
            return {"created": [], "skipped": [], "metrics": {}}

        metrics = await self.collect_metrics()
        created: list[dict[str, Any]] = []
        skipped: list[str] = []

        checks: list[tuple[str, bool]] = [
            (
                "high_retry_rate",
                metrics["total_validations"] > 0 and metrics["avg_attempts"] > 2.5,
            ),
            (
                "low_pass_rate",
                metrics["total_validations"] > 0 and metrics["pass_rate"] < 0.75,
            ),
            (
                "low_quality_score",
                metrics["total_validations"] > 0 and metrics["avg_quality_score"] < 50,
            ),
            (
                "high_llm_cost",
                metrics["monthly_cost_usd"] > 25.0,
            ),
            (
                "agent_failure_spike",
                metrics["total_executions"] >= 5 and metrics["failure_rate"] > 0.2,
            ),
            (
                "orchestration_failures",
                metrics["orchestration_total"] > 0 and metrics["orchestration_failed"] > 0,
            ),
            (
                "tool_execution_failures",
                metrics["tool_total"] >= 3 and metrics["tool_failure_count"] > 0,
            ),
        ]

        for alert_type, triggered in checks:
            if not triggered:
                continue
            if await store.find_open_alert(alert_type):
                skipped.append(alert_type)
                continue

            rule = ALERT_RULES[alert_type]
            message = str(rule["message"]).format(
                avg_attempts=metrics["avg_attempts"],
                pass_rate=metrics["pass_rate"],
                pass_rate_pct=metrics["pass_rate_pct"],
                avg_quality_score=metrics["avg_quality_score"],
                monthly_cost_usd=metrics["monthly_cost_usd"],
                failure_rate_pct=metrics["failure_rate_pct"],
                failure_count=metrics["failure_count"],
                total_executions=metrics["total_executions"],
                failed=metrics["orchestration_failed"],
                total=metrics["orchestration_total"],
            )

            row = await store.create_alert(
                alert_type=alert_type,
                severity=str(rule["severity"]),
                title=str(rule["title"]),
                message=message,
                source=str(rule["source"]),
            )
            if not row:
                skipped.append(alert_type)
                continue
            created.append(row)

            if rule.get("create_incident") and row.get("id"):
                await store.create_incident(
                    title=str(rule["title"]),
                    severity="high" if rule["severity"] == "critical" else "medium",
                    description=message,
                    source=str(rule["source"]),
                    alert_id=str(row["id"]),
                )

        return {"created": created, "skipped": skipped, "metrics": metrics}


async def run_checks(days: int = 30) -> dict[str, Any]:
    """Point d'entrée pipeline + API — exécute les règles de détection."""
    try:
        return await AlertEngine(days=days).scan()
    except Exception as exc:
        logger.warning("[AlertEngine] run_checks échoué — %s", exc)
        return {"created": [], "skipped": [], "metrics": {}, "error": str(exc)}


_engine: AlertEngine | None = None


def get_alert_engine() -> AlertEngine:
    global _engine
    if _engine is None:
        _engine = AlertEngine()
    return _engine
