"""
Pipeline CyberForge v2 — Brief → (DB/Auth/Payment) → Generator → Deploy.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agents.brief_ai import BriefAI
from agents.deploy_ai import DeployAI
from agents.generator_ai import GeneratorAI

logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
    prompt: str = Field(min_length=3)
    project_type: str = "vitrine_next"
    client_name: str = ""


async def run_pipeline(request: PipelineRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, dict):
        req = PipelineRequest.model_validate(request)
    else:
        req = request

    brief_ai = BriefAI()
    brief = await brief_ai.run(
        prompt=req.prompt,
        project_type=req.project_type,
        client_name=req.client_name,
    )
    brief["prompt"] = req.prompt

    pt = (brief.get("project_type") or req.project_type or "").strip().lower()

    if pt not in ("vitrine_next",):
        from agents import database_ai

        brief["database_schema"] = await database_ai.run(
            project_description=str(brief.get("description") or req.prompt),
            project_type=pt,
            design_system={},
        )

    if pt in ("application_web", "real_app"):
        from agents import auth_ai

        brief["auth_schema"] = await auth_ai.run(
            project_description=str(brief.get("description") or req.prompt),
            project_type=pt,
            database_schema=brief.get("database_schema") or {},
        )

    if pt in ("ecommerce", "site_reservation"):
        from agents import payment_ai

        brief["payment_config"] = await payment_ai.run(
            project_description=str(brief.get("description") or req.prompt),
            project_type=pt,
            database_schema=brief.get("database_schema") or {},
        )

    generator = GeneratorAI()
    result = await generator.run(brief)
    if not result.get("success") or not result.get("html"):
        return {
            "url": "",
            "html": "",
            "success": False,
            "brief": brief,
            "error": "GeneratorAI n'a pas produit de HTML valide.",
        }

    deploy = DeployAI()
    deployed = await deploy.run(
        result["html"],
        title=str(brief.get("client_name") or req.client_name or "CyberForge"),
        sector=str(brief.get("sector") or ""),
    )
    return {
        "url": deployed.get("url", ""),
        "html": deployed.get("html") or result["html"],
        "success": bool(deployed.get("success")),
        "brief": brief,
        "unlock_url": deployed.get("unlock_url"),
        "demo_token": deployed.get("demo_token"),
        "demo_password": deployed.get("demo_password"),
        "error": deployed.get("error"),
    }
