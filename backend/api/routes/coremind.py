"""
Route CoreMindAI — analyse, génération et flow complet.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.coremind_agent import CoreMindAgent, CoreMindAnalysis, CoreMindRunResult, ProjectType
from agents.pipeline_graph import run_generation_pipeline
from agents.demo_quality import preview_html_from_seed_dict
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
    generation_mode: str | None = Field(
        default=None,
        description=(
            "Mode : 'client_demo' (défaut), 'real_app' (React), "
            "'vitrine_next' (scaffold Next.js + site.json)"
        ),
    )
    project_id: str | None = Field(
        default=None,
        max_length=128,
        description="Identifiant projet pour le suivi des coûts API",
    )
    inspiration_brief: str | None = Field(
        default=None,
        max_length=24_000,
        description="Brief enrichi (Firecrawl clone-inspiration) pour ArchitectAI",
    )
    firecrawl_result: dict[str, Any] | None = Field(
        default=None,
        description="Données structurées Firecrawl (palette, couleurs, images) pour DesignSystemAI",
    )
    personal_project: bool = Field(
        default=False,
        description="Projet perso — déploiement Pages dédié si vraie app",
    )
    pages_project_slug: str | None = Field(
        default=None,
        max_length=64,
        description="Slug Cloudflare Pages dédié (ex. capcore-pro-site)",
    )
    project_title: str | None = Field(
        default=None,
        max_length=200,
        description="Titre du projet pour l'export",
    )
    openhands_enabled: bool | None = Field(
        default=None,
        description=(
            "Active OpenHands pour projets complexes (≥ 7/10) en real_app / application_web. "
            "None = activé par défaut si clé Anthropic présente."
        ),
    )
    playwright_enabled: bool | None = Field(
        default=None,
        description="Active les tests E2E Playwright après TestPilotAI. None = activé par défaut.",
    )
    lighthouse_enabled: bool | None = Field(
        default=None,
        description="Active l'audit Lighthouse après Playwright. None = activé par défaut.",
    )
    research_enabled: bool | None = Field(
        default=None,
        description="Active ResearchAI (Brave + Exa) après ArchitectAI. None = activé par défaut.",
    )
    stitch_enabled: bool | None = Field(
        default=None,
        description="Active StitchAI (maquettes Google) après ResearchAI. None = activé par défaut.",
    )


class CoreMindRunResponse(CoreMindRunResult):
    """Réponse du flow complet, avec persistance Supabase optionnelle."""

    persistence: PersistenceResult | None = None


class PreviewHtmlRequest(BaseModel):
    """Seed + contexte pour régénérer l'aperçu premium (panneau Personnaliser)."""

    demo_seed: dict = Field(..., description="Seed sérialisée du projet")
    prompt: str | None = Field(default=None, max_length=8000)
    project_type_label: str | None = Field(default=None, max_length=200)


class PreviewHtmlResponse(BaseModel):
    html: str = Field(..., min_length=100)


class CoreMindGenerateRequest(BaseModel):
    """Corps de requête pour la génération de code CoreMindAI."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=12000,
        description="Description du code ou projet à générer",
    )
    project_id: str | None = Field(
        default=None,
        max_length=128,
        description="Identifiant projet pour le suivi des coûts API",
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
        return await agent.generate_code(body.prompt, project_id=body.project_id)
    except CodeGenServiceError as exc:
        raise _codegen_http_error(exc) from exc


@router.post("/agents/coremind/preview-html", response_model=PreviewHtmlResponse)
async def preview_demo_html(body: PreviewHtmlRequest) -> PreviewHtmlResponse:
    """Régénère l'aperçu premium (template de la seed) avec personnalisation."""
    try:
        html = preview_html_from_seed_dict(
            body.demo_seed,
            title=body.project_type_label or "Démo client",
            user_prompt=(body.prompt or "").strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PreviewHtmlResponse(html=html)


@router.post("/agents/coremind/run", response_model=CoreMindRunResponse)
async def run_coremind_flow(body: CoreMindRequest) -> CoreMindRunResponse:
    """
    Flow complet CoreMindAI : analyse → sélection du modèle → génération de code.
    Enregistre automatiquement dans Supabase si configuré.
    """
    try:
        result = await run_generation_pipeline(
            body.prompt,
            project_type_hint=body.project_type,
            generation_mode=body.generation_mode,
            openhands_enabled=body.openhands_enabled,
            playwright_enabled=body.playwright_enabled,
            lighthouse_enabled=body.lighthouse_enabled,
            research_enabled=body.research_enabled,
            stitch_enabled=body.stitch_enabled,
            project_id=body.project_id,
            inspiration_brief=body.inspiration_brief,
            firecrawl_result=body.firecrawl_result,
            personal_project=body.personal_project,
            pages_project_slug=body.pages_project_slug,
            project_title=body.project_title,
        )
        if result.demo_pipeline is not None:
            logger.info(
                "POST /agents/coremind/run — demo_pipeline=%s",
                result.demo_pipeline.model_dump(),
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

    if persistence is not None:
        from tools.export_demo_persistence import persist_pipeline_cloudflare_demo

        try:
            await persist_pipeline_cloudflare_demo(
                run_result=result,
                generation_id=persistence.generation_id,
            )
        except Exception as exc:
            logger.warning("Persistance démo ExportAI ignorée : %s", exc)

    return CoreMindRunResponse(**result.model_dump(), persistence=persistence)
