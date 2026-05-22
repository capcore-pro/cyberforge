"""
Route CoreMindAI — analyse, génération et flow complet.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.coremind_agent import CoreMindAgent, CoreMindAnalysis, CoreMindRunResult, ProjectType
from security.llm_secrets import LLM_KEYS_UNAVAILABLE_MSG
from db.supabase_store import PersistenceResult, SupabaseStoreError, get_supabase_store
from tools.codegen_service import CodeGenService, CodeGenServiceError, CodeGenerateResult

logger = logging.getLogger(__name__)

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


class CoreMindRunResponse(CoreMindRunResult):
    """Réponse du flow complet, avec persistance Supabase optionnelle."""

    persistence: PersistenceResult | None = None


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
        raise HTTPException(status_code=503, detail=LLM_KEYS_UNAVAILABLE_MSG)
    agent = CoreMindAgent()
    try:
        return await agent.generate_code(body.prompt)
    except CodeGenServiceError as exc:
        raise _codegen_http_error(exc) from exc


@router.post("/agents/coremind/run", response_model=CoreMindRunResponse)
async def run_coremind_flow(body: CoreMindRequest) -> CoreMindRunResponse:
    """
    Flow complet CoreMindAI : analyse → sélection du modèle → génération de code.
    Enregistre automatiquement dans Supabase si configuré.
    """
    agent = CoreMindAgent()
    try:
        result = await agent.run_flow(body.prompt, body.project_type)
        if result.demo_quality is not None:
            logger.info(
                "POST /agents/coremind/run — demo_quality=%s",
                result.demo_quality.model_dump(),
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CodeGenServiceError as exc:
        raise _codegen_http_error(exc) from exc

    persistence: PersistenceResult | None = None
    store = get_supabase_store()
    if store.is_configured():
        try:
            project_type = body.project_type or result.analysis.project_type
            persistence = await store.save_generation(
                body.prompt.strip(),
                project_type,
                result,
            )
        except SupabaseStoreError as exc:
            logger.warning("Sauvegarde Supabase ignorée : %s", exc)

    return CoreMindRunResponse(**result.model_dump(), persistence=persistence)
