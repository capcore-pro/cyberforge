"""
Planning Engine — plan d'exécution déterministe avant le pipeline.
"""

from __future__ import annotations

from typing import Any


def _get_workflow_id(project_type: str) -> str:
    pt = (project_type or "").strip().lower().replace("-", "_")
    mapping = {
        "vitrine_next": "vitrine_simple",
        "ecommerce": "ecommerce",
        "site_reservation": "reservation",
        "application_web": "app_web_crm",
        "crm": "app_web_crm",
        "real_app": "app_web_crm",
        "extension_navigateur": "extension_navigateur",
    }
    return mapping.get(pt, "vitrine_simple")


class PlanningEngine:
    """Analyse le brief et détermine le plan d'exécution optimal."""

    def build_plan(self, brief: dict[str, Any]) -> dict[str, Any]:
        b = brief or {}
        project_type = str(b.get("project_type") or "vitrine_next").strip().lower()
        agents: list[str] = ["brief", "design_system"]

        if project_type not in ("vitrine_next",):
            agents.append("database")
        if project_type in ("application_web", "crm", "real_app"):
            agents.append("auth")
        if project_type in ("ecommerce", "site_reservation"):
            agents.append("payment")

        if project_type == "extension_navigateur":
            agents = ["brief", "extension_builder", "deploy"]
        else:
            agents += ["generator", "supervisor", "deploy"]

        cost_map = {
            "brief": 0.002,
            "design_system": 0.0,
            "database": 0.008,
            "auth": 0.008,
            "payment": 0.008,
            "generator": 0.08,
            "supervisor": 0.0,
            "deploy": 0.001,
            "extension_builder": 0.0,
        }
        estimated_cost = sum(cost_map.get(agent, 0.0) for agent in agents)

        risks: list[str] = []
        description = str(b.get("description") or "")
        if len(description) < 100:
            risks.append("description_too_short")
        if not str(b.get("couleur_primaire") or "").strip():
            risks.append("missing_primary_color")
        if project_type in ("application_web", "crm") and not b.get("services"):
            risks.append("missing_services_for_webapp")

        if len(risks) >= 2:
            risk_level = "high"
        elif len(risks) == 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "workflow_id": _get_workflow_id(project_type),
            "agents": agents,
            "estimated_cost_usd": round(estimated_cost, 4),
            "estimated_duration_ms": len(agents) * 8000,
            "risk_level": risk_level,
            "risk_factors": risks,
        }
