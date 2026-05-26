"""
Statut des agents IA — pipeline LangGraph toujours actif côté backend.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["agents"])

PIPELINE_AGENT_IDS: tuple[str, ...] = (
    "architect",
    "builder",
    "coremind",
    "visionui",
    "bughunter",
    "autofix",
    "testpilot",
    "export",
)

TOTAL_AGENTS = 8

_AGENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("coremind", "CoreMindAI", "Orchestrateur central du pipeline LangGraph."),
    ("architect", "ArchitectAI", "Analyse du prompt et choix du template premium."),
    ("builder", "BuilderAI", "Génération de code et scaffolding de modules."),
    ("bughunter", "BugHunterAI", "Vérification du HTML généré avant livraison."),
    ("autofix", "AutoFixAI", "Correction automatique des livrables défectueux."),
    ("visionui", "VisionUI", "Interfaces visuelles et design system cyber."),
    ("testpilot", "TestPilotAI", "Tests automatisés et validation de régression."),
    ("export", "ExportAI", "Export de rapports et documentation client."),
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
    """
    Les huit agents du pipeline LangGraph sont toujours opérationnels (ACTIF).
    """
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
