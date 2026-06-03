"""
Statut des agents IA — pipeline v2.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.secrets import _merge_configured_flags
from config import get_settings
from security.secret_vault import get_secret_vault

router = APIRouter(tags=["agents"])

PIPELINE_AGENT_IDS: tuple[str, ...] = (
    "brief",
    "database",
    "auth",
    "payment",
    "generator",
    "deploy",
)

TOTAL_AGENTS = len(PIPELINE_AGENT_IDS)

_AGENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("brief", "BriefAI", "Brief structuré + Firecrawl (concurrents)."),
    ("database", "DatabaseAI", "Schéma Supabase si app / ecommerce / réservation."),
    ("auth", "AuthAI", "Auth Supabase si application web."),
    ("payment", "PaymentAI", "Stripe si ecommerce / réservation."),
    ("generator", "GeneratorAI", "HTML complet en un appel Claude."),
    ("deploy", "DeployAI", "Images Pexels + déploiement Cloudflare Pages."),
)


class AgentStatusItem(BaseModel):
    id: str
    name: str
    description: str
    status: str = Field(description="active | standby")
    in_pipeline: bool = False


class AgentsStatusResponse(BaseModel):
    total_agents: int
    active_count: int
    pipeline_agent_ids: list[str]
    agents: list[AgentStatusItem]


def _configured_flags() -> dict[str, bool]:
    vault = get_secret_vault().status()
    settings = get_settings()
    return _merge_configured_flags(vault.configured, settings)


@router.get("/agents/status", response_model=AgentsStatusResponse)
async def get_agents_status() -> AgentsStatusResponse:
    pipeline_set = set(PIPELINE_AGENT_IDS)
    configured = _configured_flags()
    agents: list[AgentStatusItem] = []
    active_count = 0
    for agent_id, name, description in _AGENT_CATALOG:
        in_pipeline = agent_id in pipeline_set
        is_active = in_pipeline and (
            agent_id != "brief" or configured.get("anthropic", True)
        )
        if is_active:
            active_count += 1
        agents.append(
            AgentStatusItem(
                id=agent_id,
                name=name,
                description=description,
                status="active" if is_active else "standby",
                in_pipeline=in_pipeline,
            )
        )
    return AgentsStatusResponse(
        total_agents=TOTAL_AGENTS,
        active_count=active_count,
        pipeline_agent_ids=list(PIPELINE_AGENT_IDS),
        agents=agents,
    )
