"""
POST /api/generate — pipeline CyberForge v2 (async + SSE).
POST /api/generate/sync — pipeline synchrone (rétrocompatibilité / tests).
GET  /api/generate/stream/{generation_id} — événements SSE temps réel.
POST /api/generator/generate-prompt — prompt enrichi depuis une idée courte.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import anthropic
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.generation_stream import generation_event_store
from config import get_settings
from pipeline import PipelineRequest, run_pipeline
from security.llm_secrets import get_effective_llm_key

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])

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
    stripe_publishable_key: str | None = None
    sync: bool | None = Field(
        default=None,
        description="Si true, exécute le pipeline de façon synchrone (legacy).",
    )


class GenerateStartResponse(BaseModel):
    generation_id: str
    status: str = "started"


class GenerateResponse(BaseModel):
    url: str = ""
    html: str = ""
    success: bool = False
    error: str | None = None
    unlock_url: str | None = None
    demo_token: str | None = None
    demo_password: str | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None


class GeneratePromptFromIdeaRequest(BaseModel):
    idea: str = Field(..., min_length=3, max_length=4000)
    project_type: str = "vitrine_next"


class GeneratePromptFromIdeaResponse(BaseModel):
    prompt: str


def _pipeline_request(body: GenerateRequest) -> PipelineRequest:
    return PipelineRequest(
        prompt=body.prompt,
        project_type=body.project_type,
        client_name=body.client_name,
        generation_mode=body.generation_mode,
        inspiration_brief=body.inspiration_brief,
        firecrawl_result=body.firecrawl_result,
        stripe_publishable_key=body.stripe_publishable_key,
    )


def _to_generate_response(result: dict[str, Any]) -> GenerateResponse:
    return GenerateResponse(
        url=str(result.get("url") or ""),
        html=str(result.get("html") or ""),
        success=bool(result.get("success")),
        error=result.get("error"),
        unlock_url=result.get("unlock_url"),
        demo_token=result.get("demo_token"),
        demo_password=result.get("demo_password"),
        duration_ms=result.get("duration_ms"),
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
        total_tokens=result.get("total_tokens"),
        estimated_cost_usd=result.get("estimated_cost_usd"),
    )


async def _run_pipeline_background(generation_id: str, body: GenerateRequest) -> None:
    try:
        await run_pipeline(_pipeline_request(body), generation_id=generation_id)
    except Exception as exc:
        logger.exception("Pipeline async generation_id=%s", generation_id)
        if generation_event_store.exists(generation_id):
            session = generation_event_store.get_session(generation_id)
            if session and not session.terminal:
                await generation_event_store.emit(
                    generation_id,
                    "error",
                    {"message": str(exc)},
                )


def _parse_last_event_id(request: Request) -> int:
    raw = (request.headers.get("last-event-id") or "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _sse_message(seq: int, event_type: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"id: {seq}\nevent: {event_type}\ndata: {payload}\n\n"


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


@router.post("/generate/sync", response_model=GenerateResponse)
async def generate_site_sync(body: GenerateRequest) -> GenerateResponse:
    """Pipeline synchrone — JSON final (tests unitaires, scripts)."""
    try:
        result = await run_pipeline(_pipeline_request(body))
    except Exception as exc:
        logger.exception("POST /api/generate/sync")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _to_generate_response(result)


@router.post("/generate")
async def generate_site(body: GenerateRequest) -> GenerateStartResponse | GenerateResponse:
    """
    Démarre une génération async (SSE) ou synchrone si body.sync=true.
    """
    if body.sync:
        return await generate_site_sync(body)

    generation_id = str(uuid4())
    await generation_event_store.create(generation_id)
    asyncio.create_task(_run_pipeline_background(generation_id, body))
    return GenerateStartResponse(generation_id=generation_id, status="started")


@router.get("/generate/stream/{generation_id}")
async def generate_stream(generation_id: str, request: Request) -> StreamingResponse:
    if not generation_event_store.exists(generation_id):
        raise HTTPException(status_code=404, detail="Génération introuvable.")

    after_seq = _parse_last_event_id(request)
    generation_event_store.register_subscriber(generation_id)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for seq, event_type, data in generation_event_store.iter_events(
                generation_id,
                after_seq=after_seq,
            ):
                yield _sse_message(seq, event_type, data)
                if event_type in ("done", "error"):
                    break
        finally:
            generation_event_store.unregister_subscriber(generation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
