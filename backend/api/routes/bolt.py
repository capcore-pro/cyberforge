"""
Route outil Bolt.new — génération de code à partir d'un prompt.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools.bolt_service import BoltGenerateResult, BoltService, BoltServiceError

router = APIRouter(tags=["tools"])


class BoltGenerateRequest(BaseModel):
    """Corps de requête pour la génération Bolt.new."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=12000,
        description="Description du projet ou composant à générer",
    )


@router.post("/tools/bolt", response_model=BoltGenerateResult)
async def generate_with_bolt(body: BoltGenerateRequest) -> BoltGenerateResult:
    """Envoie un prompt à Bolt.new (ou repli LLM) et retourne le code généré."""
    service = BoltService()
    if not service.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Service Bolt non configuré. Ajoutez BOLT_API_KEY et BOLT_API_BASE_URL "
                "ou OPENAI_API_KEY / ANTHROPIC_API_KEY dans .env"
            ),
        )
    try:
        return await service.generate(body.prompt)
    except BoltServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
