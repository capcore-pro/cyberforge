"""
Route CoreMindAI — analyse de prompt et recommandation d'outil.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.coremind_agent import CoreMindAgent, CoreMindAnalysis

router = APIRouter(tags=["agents"])


class CoreMindRequest(BaseModel):
    """Corps de requête pour l'analyse CoreMindAI."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=8000,
        description="Description du projet ou besoin utilisateur",
    )


@router.post("/agents/coremind", response_model=CoreMindAnalysis)
async def analyze_with_coremind(body: CoreMindRequest) -> CoreMindAnalysis:
    """
    Analyse un prompt utilisateur et retourne type de projet,
    outil recommandé (Bolt.new / Lovable / v0), complexité et prochaines étapes.
    """
    agent = CoreMindAgent()
    try:
        return await agent.analyze(body.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
