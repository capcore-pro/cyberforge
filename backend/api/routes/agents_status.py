"""
Statut des agents IA — pipeline v2.
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel, Field

from db.agent_registry_store import get_agent_registry_store
from db.supabase_store import SupabaseStoreError
from security.agent_readiness import (
    agent_is_active,
    brevo_ready,
    llm_router_status,
    replicate_ready,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

_AGENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("brief", "BriefAI", "Brief structuré + Firecrawl (concurrents)."),
    ("supervisor", "SupervisorAI", "Validation binaire à chaque étape du pipeline."),
    ("generator", "GeneratorAI", "HTML complet en un appel Claude."),
    ("deploy", "DeployAI", "Images Pexels + déploiement Cloudflare Pages."),
    ("database", "DatabaseAI", "Schéma Supabase si app / ecommerce / réservation."),
    ("auth", "AuthAI", "Auth Supabase si application web."),
    ("payment", "PaymentAI", "Stripe si ecommerce / réservation."),
    ("email", "EmailAI", "Notifications Brevo (déploiement, commande, réservation)."),
    ("media", "MediaAI", "Upscaling Replicate, génération image et recherche Pexels."),
    ("electron", "ElectronAI", "Empaquetage application desktop (.exe)."),
    ("design_system", "DesignSystemAI", "Tokens CSS cohérents selon le type de projet."),
)

_EMAIL_STANDBY_NOTE = "EmailAI en standby — configurer BREVO_API_KEY"
_MEDIA_STANDBY_NOTE = "MediaAI en standby — configurer REPLICATE_API_KEY dans Paramètres"

PIPELINE_AGENT_IDS: tuple[str, ...] = tuple(agent_id for agent_id, _, _ in _AGENT_CATALOG)


class AgentStatusItem(BaseModel):
    id: str
    name: str
    description: str
    status: str = Field(description="active | standby")
    in_pipeline: bool = False
    category: str | None = None
    model: str | None = None
    provider: str | None = None
    capabilities: list[str] | None = None


class LLMRouterStatus(BaseModel):
    active: bool
    available_providers: list[str]
    fallback_count: int
    task_types: list[str]


class AgentsStatusResponse(BaseModel):
    total_agents: int
    active_count: int
    pipeline_agent_ids: list[str]
    agents: list[AgentStatusItem]
    llm_router: LLMRouterStatus
    source: str = Field(description="registry | fallback")


def _parse_capabilities(raw: object) -> list[str] | None:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return None


def _build_status_item(
    agent_id: str,
    name: str,
    description: str,
    *,
    in_pipeline: bool,
    category: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    capabilities: list[str] | None = None,
) -> AgentStatusItem:
    is_active = in_pipeline and agent_is_active(agent_id)
    desc = description
    if agent_id == "email" and not brevo_ready():
        desc = f"{description} — {_EMAIL_STANDBY_NOTE}"
    if agent_id == "media" and not replicate_ready():
        desc = f"{description} — {_MEDIA_STANDBY_NOTE}"
    return AgentStatusItem(
        id=agent_id,
        name=name,
        description=desc,
        status="active" if is_active else "standby",
        in_pipeline=in_pipeline,
        category=category,
        model=model,
        provider=provider,
        capabilities=capabilities,
    )


async def _load_registry_catalog() -> list[dict] | None:
    store = get_agent_registry_store()
    if not store.is_configured():
        return None
    try:
        rows = await store.list_all()
        return rows if rows else None
    except SupabaseStoreError as exc:
        logger.warning("agents/status registry indisponible: %s", exc)
        return None


def _build_from_fallback_catalog() -> tuple[list[AgentStatusItem], list[str]]:
    pipeline_set = set(PIPELINE_AGENT_IDS)
    agents: list[AgentStatusItem] = []
    for agent_id, name, description in _AGENT_CATALOG:
        in_pipeline = agent_id in pipeline_set
        agents.append(
            _build_status_item(agent_id, name, description, in_pipeline=in_pipeline)
        )
    return agents, list(PIPELINE_AGENT_IDS)


def _build_from_registry(rows: list[dict]) -> tuple[list[AgentStatusItem], list[str]]:
    agents: list[AgentStatusItem] = []
    pipeline_ids: list[str] = []
    for row in rows:
        agent_id = str(row.get("agent_id") or "")
        if not agent_id:
            continue
        in_pipeline = bool(row.get("in_pipeline"))
        if in_pipeline:
            pipeline_ids.append(agent_id)
        agents.append(
            _build_status_item(
                agent_id,
                str(row.get("name") or agent_id),
                str(row.get("description") or ""),
                in_pipeline=in_pipeline,
                category=row.get("category"),
                model=row.get("model"),
                provider=row.get("provider"),
                capabilities=_parse_capabilities(row.get("capabilities")),
            )
        )
    return agents, pipeline_ids


@router.get("/agents/status", response_model=AgentsStatusResponse)
async def get_agents_status() -> AgentsStatusResponse:
    registry_rows = await _load_registry_catalog()
    if registry_rows:
        agents, pipeline_agent_ids = _build_from_registry(registry_rows)
        source = "registry"
    else:
        agents, pipeline_agent_ids = _build_from_fallback_catalog()
        source = "fallback"

    active_count = sum(1 for a in agents if a.status == "active")
    router_info = llm_router_status()
    return AgentsStatusResponse(
        total_agents=len(agents),
        active_count=active_count,
        pipeline_agent_ids=pipeline_agent_ids,
        agents=agents,
        llm_router=LLMRouterStatus(
            active=bool(router_info.get("active")),
            available_providers=list(router_info.get("available_providers") or []),
            fallback_count=int(router_info.get("fallback_count") or 0),
            task_types=list(router_info.get("task_types") or []),
        ),
        source=source,
    )
