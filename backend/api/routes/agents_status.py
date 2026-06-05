"""
Statut des agents IA — pipeline v2.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import get_settings

load_dotenv(override=True)

router = APIRouter(tags=["agents"])

_AGENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("brief", "BriefAI", "Brief structuré + Firecrawl (concurrents)."),
    ("supervisor", "SupervisorAI", "Validation binaire à chaque étape du pipeline."),
    ("generator", "GeneratorAI", "HTML complet en un appel Claude."),
    ("deploy", "DeployAI", "Images Pexels + déploiement Cloudflare Pages."),
    ("database", "DatabaseAI", "Schéma Supabase si app / ecommerce / réservation."),
    ("auth", "AuthAI", "Auth Supabase si application web."),
    ("payment", "PaymentAI", "Stripe si ecommerce / réservation."),
    ("electron", "ElectronAI", "Empaquetage application desktop (.exe)."),
)

PIPELINE_AGENT_IDS: tuple[str, ...] = tuple(agent_id for agent_id, _, _ in _AGENT_CATALOG)


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


def _has_env(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _anthropic_ready() -> bool:
    return _has_env("ANTHROPIC_API_KEY")


def _deploy_ready() -> bool:
    return _has_env("PEXELS_API_KEY") and _has_env("CLOUDFLARE_API_TOKEN")


def _supabase_ready() -> bool:
    return _has_env("SUPABASE_URL") or get_settings().supabase_configured()


def _stripe_ready() -> bool:
    return _has_env("STRIPE_SECRET_KEY")


def _agent_is_active(agent_id: str) -> bool:
    """Actif si les clés requises sont présentes dans l'environnement."""
    if agent_id == "electron":
        return True
    if agent_id in ("brief", "generator", "supervisor"):
        return _anthropic_ready()
    if agent_id == "deploy":
        return _deploy_ready()
    if agent_id in ("database", "auth"):
        return _supabase_ready()
    if agent_id == "payment":
        return _stripe_ready()
    return False


@router.get("/agents/status", response_model=AgentsStatusResponse)
async def get_agents_status() -> AgentsStatusResponse:
    pipeline_set = set(PIPELINE_AGENT_IDS)
    agents: list[AgentStatusItem] = []
    for agent_id, name, description in _AGENT_CATALOG:
        in_pipeline = agent_id in pipeline_set
        is_active = in_pipeline and _agent_is_active(agent_id)
        agents.append(
            AgentStatusItem(
                id=agent_id,
                name=name,
                description=description,
                status="active" if is_active else "standby",
                in_pipeline=in_pipeline,
            )
        )
    active_count = sum(1 for a in agents if a.status == "active")
    return AgentsStatusResponse(
        total_agents=len(PIPELINE_AGENT_IDS),
        active_count=active_count,
        pipeline_agent_ids=list(PIPELINE_AGENT_IDS),
        agents=agents,
    )
