"""
POST /api/generate — pipeline CyberForge v2 (Brief → Generator → Deploy).
POST /api/generator/generate-prompt — prompt enrichi depuis une idée courte.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import anthropic
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from pipeline import PipelineRequest, run_pipeline
from security.llm_secrets import get_effective_llm_key

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])

# Sonnet uniquement pour l'enrichissement d'idée → prompt (qualité rédactionnelle).
PROMPT_ENRICH_MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
PROMPT_ENRICH_MAX_TOKENS = 1000

PROMPT_ENRICH_SYSTEM = """Tu es un expert en création de sites web.
À partir de cette idée courte, génère un prompt détaillé pour créer
un site web professionnel. Inclus : nom du client, secteur, services,
ambiance visuelle, couleurs suggérées, public cible.
Réponds uniquement avec le prompt enrichi, sans commentaire."""


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3)
    project_type: str = "vitrine_next"
    client_name: str = ""
    generation_mode: str | None = None
    inspiration_brief: str | None = None
    firecrawl_result: dict[str, Any] | None = None


class GenerateResponse(BaseModel):
    url: str = ""
    html: str = ""
    success: bool = False
    error: str | None = None
    unlock_url: str | None = None
    demo_token: str | None = None
    demo_password: str | None = None


class GeneratePromptFromIdeaRequest(BaseModel):
    idea: str = Field(..., min_length=3, max_length=4000)
    project_type: str = "vitrine_next"


class GeneratePromptFromIdeaResponse(BaseModel):
    prompt: str


async def _call_claude_enriched_prompt(*, idea: str, project_type: str) -> str:
    api_key = get_effective_llm_key("ANTHROPIC_API_KEY", get_settings())
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY non configurée.",
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_message = (
        f"## Idée courte\n{idea.strip()}\n\n"
        f"## Type de projet\n{project_type.strip()}"
    )

    def _do_call() -> str:
        response = client.messages.create(
            model=PROMPT_ENRICH_MODEL,
            max_tokens=PROMPT_ENRICH_MAX_TOKENS,
            system=PROMPT_ENRICH_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    raw = await asyncio.to_thread(_do_call)
    if not raw:
        raise HTTPException(status_code=502, detail="Réponse Claude vide.")
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if len(lines) > 2 else lines[1:]).strip()
    return cleaned


@router.post("/generator/generate-prompt", response_model=GeneratePromptFromIdeaResponse)
async def generate_prompt_from_idea(
    body: GeneratePromptFromIdeaRequest,
) -> GeneratePromptFromIdeaResponse:
    try:
        prompt = await _call_claude_enriched_prompt(
            idea=body.idea,
            project_type=body.project_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("POST /api/generator/generate-prompt")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GeneratePromptFromIdeaResponse(prompt=prompt)


@router.post("/generate", response_model=GenerateResponse)
async def generate_site(body: GenerateRequest) -> GenerateResponse:
    try:
        result = await run_pipeline(
            PipelineRequest(
                prompt=body.prompt,
                project_type=body.project_type,
                client_name=body.client_name,
                generation_mode=body.generation_mode,
                inspiration_brief=body.inspiration_brief,
                firecrawl_result=body.firecrawl_result,
            )
        )
    except Exception as exc:
        logger.exception("POST /api/generate")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GenerateResponse(
        url=str(result.get("url") or ""),
        html=str(result.get("html") or ""),
        success=bool(result.get("success")),
        error=result.get("error"),
        unlock_url=result.get("unlock_url"),
        demo_token=result.get("demo_token"),
        demo_password=result.get("demo_password"),
    )
