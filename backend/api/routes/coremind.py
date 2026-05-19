"""
Route CoreMindAI — analyse, génération et flow complet.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.coremind_agent import CoreMindAgent, CoreMindAnalysis, CoreMindRunResult, ProjectType
from tools.codegen_service import CodeGenService, CodeGenServiceError, CodeGenerateResult

router = APIRouter(tags=["agents"])


def _codegen_http_error(exc: CodeGenServiceError) -> HTTPException:
    message = str(exc)
    if "clé LLM" in message:
        status = 503
    elif "timeout" in message.lower():
        status = 504
    else:
        status = 422
    return HTTPException(status_code=status, detail=message)


class CoreMindRequest(BaseModel):
    """Corps de requête pour l'analyse CoreMindAI."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=8000,
        description="Description du projet ou besoin utilisateur",
    )
    project_type: ProjectType | None = Field(
        default=None,
        description="Type de projet choisi dans le Générateur (optionnel)",
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
    """Analyse un prompt utilisateur (type, outil, complexité)."""
    agent = CoreMindAgent()
    try:
        return await agent.analyze(body.prompt, body.project_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agents/coremind/generate", response_model=CodeGenerateResult)
async def generate_code_with_coremind(
    body: CoreMindGenerateRequest,
) -> CodeGenerateResult:
    """Génère du code via le routage multi-modèles CoreMindAI."""
    service = CodeGenService()
    if not service.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Aucune clé LLM dans backend/.env : DEEPSEEK_API_KEY, "
                "GOOGLE_GENERATIVE_AI_API_KEY ou ANTHROPIC_API_KEY."
            ),
        )
    agent = CoreMindAgent()
    try:
        return await agent.generate_code(body.prompt)
    except CodeGenServiceError as exc:
        raise _codegen_http_error(exc) from exc


@router.post("/agents/coremind/run", response_model=CoreMindRunResult)
async def run_coremind_flow(body: CoreMindRequest) -> CoreMindRunResult:
    """
    Flow complet CoreMindAI : analyse → sélection du modèle → génération de code.
    """
    agent = CoreMindAgent()
    try:
        return await agent.run_flow(body.prompt, body.project_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CodeGenServiceError as exc:
        raise _codegen_http_error(exc) from exc
