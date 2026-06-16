"""
Routes API — Agent Builder (custom agents).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db.custom_agent_store import get_custom_agent_store
from db.supabase_store import SupabaseStoreError
from llm.base_provider import LLMRequest
from llm.router import get_llm_router
from tools.llm_pricing import compute_llm_cost_usd

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent_builder"])


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _resolve_provider(model: str) -> str:
    key = (model or "").strip().lower()
    if key.startswith("claude-"):
        return "anthropic"
    if key.startswith("mistral-"):
        return "mistral"
    # modèles locaux via Ollama
    if "ollama" in key or key.startswith(("qwen", "qwen3", "deepseek")):
        return "ollama"
    # fallback par défaut
    return "anthropic"


class CustomAgentUpsert(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(..., min_length=10, max_length=20000)
    model: str = Field(..., min_length=2, max_length=255)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=500, le=4000)
    tools: list[str] = Field(default_factory=list)
    is_active: bool = True


class CustomAgentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    tools: list[str]
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None


def _row_to_agent(row: dict[str, Any]) -> CustomAgentResponse:
    tools_raw = row.get("tools")
    tools = tools_raw if isinstance(tools_raw, list) else []
    return CustomAgentResponse(
        id=str(row.get("id") or ""),
        name=str(row.get("name") or ""),
        description=row.get("description"),
        system_prompt=str(row.get("system_prompt") or ""),
        model=str(row.get("model") or ""),
        temperature=float(row.get("temperature") or 0.7),
        max_tokens=int(row.get("max_tokens") or 2048),
        tools=[str(x) for x in tools],
        is_active=bool(row.get("is_active")),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("/agents/custom", response_model=CustomAgentResponse)
async def create_custom_agent(body: CustomAgentUpsert) -> CustomAgentResponse:
    store = get_custom_agent_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.create_agent(body.model_dump())
        return _row_to_agent(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/agents/custom")
async def list_custom_agents() -> dict:
    store = get_custom_agent_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        rows = await store.list_agents()
        return {"items": [_row_to_agent(r).model_dump(mode="json") for r in rows], "count": len(rows)}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/agents/custom/{agent_id}", response_model=CustomAgentResponse)
async def get_custom_agent(agent_id: str) -> CustomAgentResponse:
    store = get_custom_agent_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_agent(agent_id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent introuvable.")
        return _row_to_agent(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/agents/custom/{agent_id}", response_model=CustomAgentResponse)
async def update_custom_agent(agent_id: str, body: CustomAgentUpsert) -> CustomAgentResponse:
    store = get_custom_agent_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        updated = await store.update_agent(agent_id, body.model_dump())
        if not updated:
            raise HTTPException(status_code=404, detail="Agent introuvable.")
        return _row_to_agent(updated)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/agents/custom/{agent_id}")
async def delete_custom_agent(agent_id: str) -> dict:
    store = get_custom_agent_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        ok = await store.delete_agent(agent_id)
        return {"deleted": bool(ok)}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class CustomAgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict[str, str]] = Field(default_factory=list)


@router.post("/agents/custom/{agent_id}/chat")
async def chat_custom_agent(agent_id: str, body: CustomAgentChatRequest) -> StreamingResponse:
    """
    Chat SSE (POST) — retourne des events 'chunk' puis 'done'.
    """
    store = get_custom_agent_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")

    row = await store.get_agent(agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent introuvable.")
    if not bool(row.get("is_active")):
        raise HTTPException(status_code=400, detail="Agent inactif.")

    system_prompt = str(row.get("system_prompt") or "").strip()
    model = str(row.get("model") or "").strip()
    temperature = _clamp(float(row.get("temperature") or 0.7), 0.0, 1.0)
    max_tokens = int(row.get("max_tokens") or 2048)
    max_tokens = max(500, min(4000, max_tokens))

    messages: list[dict[str, str]] = []
    for m in body.history:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").strip()
        content = str(m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": body.message.strip()})

    provider_hint = _resolve_provider(model)
    router_inst = get_llm_router()

    async def event_generator() -> AsyncIterator[str]:
        t0 = time.perf_counter()
        try:
            yield _sse_event("start", {"agent_id": agent_id})
            response = await router_inst.route(
                LLMRequest(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                task_type="content",
            )

            text = response.content or ""
            # pseudo-streaming : découpe stable pour UI
            chunk_size = 120
            for i in range(0, len(text), chunk_size):
                yield _sse_event("chunk", {"delta": text[i : i + chunk_size]})

            duration_ms = int((time.perf_counter() - t0) * 1000)
            cost_usd = compute_llm_cost_usd(
                response.provider,
                response.model,
                response.input_tokens,
                response.output_tokens,
            )

            # Log usage (non bloquant)
            try:
                from llm.llm_usage_service import get_llm_usage_service

                await get_llm_usage_service().record_agent(
                    agent_name=str(row.get("name") or "CustomAgent"),
                    usage={
                        "provider": response.provider,
                        "model": response.model,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "total_tokens": response.total_tokens,
                    },
                    duration_ms=duration_ms,
                    generation_id=None,
                    totals=None,
                )
            except Exception as exc:
                logger.warning("llm_usage custom agent ignoré: %s", exc)

            yield _sse_event(
                "done",
                {
                    "content": text,
                    "provider": response.provider or provider_hint,
                    "model": response.model or model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "cost_usd": cost_usd,
                    "duration_ms": duration_ms,
                },
            )
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

