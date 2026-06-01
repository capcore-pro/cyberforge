"""
Statut des agents IA — pipeline LangGraph (13 agents).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["agents"])

PIPELINE_AGENT_IDS: tuple[str, ...] = (
    "architect",
    "research",
    "stitch",
    "openhands",
    "builder",
    "coremind",
    "visionui",
    "bughunter",
    "autofix",
    "testpilot",
    "playwright",
    "lighthouse",
    "export",
)

TOTAL_AGENTS = 13

_AGENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("architect", "ArchitectAI", "Analyse du prompt et choix du template premium."),
    ("research", "ResearchAI", "Recherche Brave Search + Exa AI (secteur, concurrents)."),
    ("stitch", "StitchAI", "Maquettes visuelles HTML + screenshots (Google Stitch)."),
    ("openhands", "OpenHands", "Génération de code avancée pour projets complexes."),
    ("builder", "BuilderAI", "Génération de code v0 / DeepSeek avec référence Stitch."),
    ("coremind", "CoreMindAI", "Orchestrateur central du pipeline LangGraph."),
    ("visionui", "VisionUI", "Interfaces visuelles et design system cyber."),
    ("bughunter", "BugHunterAI", "Vérification du HTML généré avant livraison."),
    ("autofix", "AutoFixAI", "Correction automatique des livrables défectueux."),
    ("testpilot", "TestPilotAI", "Tests automatisés et validation de régression."),
    ("playwright", "Playwright", "Tests E2E Chromium headless."),
    ("lighthouse", "Lighthouse", "Audit Performance, SEO, accessibilité."),
    ("export", "ExportAI", "Export et déploiement Cloudflare / Railway."),
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


@router.get("/agents/status", response_model=AgentsStatusResponse)
async def get_agents_status() -> AgentsStatusResponse:
    """Les agents du pipeline LangGraph sont opérationnels (ACTIF)."""
    pipeline_set = set(PIPELINE_AGENT_IDS)
    agents: list[AgentStatusItem] = []
    for agent_id, name, description in _AGENT_CATALOG:
        in_pipeline = agent_id in pipeline_set
        agents.append(
            AgentStatusItem(
                id=agent_id,
                name=name,
                description=description,
                status="active" if in_pipeline else "standby",
                in_pipeline=in_pipeline,
            )
        )
    return AgentsStatusResponse(
        total_agents=TOTAL_AGENTS,
        active_count=len(PIPELINE_AGENT_IDS),
        pipeline_agent_ids=list(PIPELINE_AGENT_IDS),
        agents=agents,
    )
