"""
Route CoreMindAI — analyse de prompt et génération de code via Claude.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.coremind_agent import CoreMindAgent, CoreMindAnalysis
from tools.claude_service import ClaudeCodeResult, ClaudeService, ClaudeServiceError

router = APIRouter(tags=["agents"])


class CoreMindRequest(BaseModel):
    """Corps de requête pour l'analyse CoreMindAI."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=8000,
        description="Description du projet ou besoin utilisateur",
    )


class CoreMindGenerateRequest(BaseModel):
    """Corps de requête pour la génération de code CoreMindAI."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=12000,
        description="Description du code ou projet à générer",
    )


@router.post("/agents/coremind", response_model=CoreMindAnalysis)
async def analyze_with_coremind(body: CoreMindRequest) -> CoreMindAnalysis:
    """
    Analyse un prompt utilisateur et retourne type de projet,
    outil recommandé, complexité et prochaines étapes.
    """
    agent = CoreMindAgent()
    try:
        return await agent.analyze(body.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agents/coremind/generate", response_model=ClaudeCodeResult)
async def generate_code_with_coremind(
    body: CoreMindGenerateRequest,
) -> ClaudeCodeResult:
    """
    CoreMindAI envoie le prompt à l'API Anthropic Claude
    et retourne le code généré (modèle claude-sonnet-4-20250514 par défaut).
    """
    service = ClaudeService()
    if not service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY non configurée dans .env",
        )
    agent = CoreMindAgent()
    try:
        return await agent.generate_code(body.prompt)
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
