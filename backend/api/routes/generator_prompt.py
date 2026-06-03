"""
Générateur de prompt — aide à la rédaction du brief CyberForge (Anthropic).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from security.llm_secrets import (
    LLM_KEYS_UNAVAILABLE_MSG,
    get_effective_llm_key_for_http,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generator"])

PROMPT_MODEL = "claude-sonnet-4-5"
MAX_OUTPUT_TOKENS = 512

SYSTEM_PROMPT = """Tu es un expert en création de sites web et applications.
L'utilisateur décrit un projet. Génère un prompt professionnel détaillé
pour CyberForge en une seule phrase de 3-5 lignes maximum.
Le prompt doit inclure : nom du projet, secteur, type exact, services/produits,
ambiance visuelle, couleurs souhaitées.
Réponds UNIQUEMENT avec le prompt, sans introduction ni explication."""

_KIND_LABELS: dict[str, str] = {
    "vitrine": "Vitrine (site vitrine multi-pages)",
    "ecommerce": "E-commerce (boutique en ligne)",
    "reservation": "Réservation (agenda et créneaux en ligne)",
    "app_web": "Application web (dashboard, CRM, logique métier)",
    "desktop": "Application desktop Windows",
    "extension": "Extension navigateur Chrome / Firefox",
}


class GeneratePromptRequest(BaseModel):
    project_kind: str = Field(
        ...,
        description="vitrine | ecommerce | reservation | app_web | desktop | extension",
    )
    idea: str = Field(..., min_length=3, max_length=4000)


class GeneratePromptResponse(BaseModel):
    prompt: str


@router.post("/generator/generate-prompt", response_model=GeneratePromptResponse)
async def generate_cyberforge_prompt(body: GeneratePromptRequest) -> GeneratePromptResponse:
    kind = (body.project_kind or "").strip().lower()
    if kind not in _KIND_LABELS:
        raise HTTPException(
            status_code=422,
            detail=f"Type de projet invalide : {body.project_kind}",
        )

    settings = get_settings()
    api_key = get_effective_llm_key_for_http("ANTHROPIC_API_KEY", settings)
    if not api_key:
        raise HTTPException(status_code=503, detail=LLM_KEYS_UNAVAILABLE_MSG)

    idea = body.idea.strip()
    type_label = _KIND_LABELS[kind]
    user_message = (
        f"Type de projet CyberForge : {type_label}.\n\n"
        f"Idée de l'utilisateur :\n{idea}"
    )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": PROMPT_MODEL,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("generate-prompt Anthropic HTTP error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Impossible de contacter l'API Anthropic.",
        ) from exc

    if response.status_code >= 400:
        snippet = response.text[:400] if response.text else ""
        logger.warning(
            "generate-prompt Anthropic %s: %s",
            response.status_code,
            snippet,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Anthropic a répondu {response.status_code}.",
        )

    payload = response.json()
    blocks = payload.get("content") or []
    text = "".join(
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()

    if not text:
        raise HTTPException(
            status_code=502,
            detail="Réponse Anthropic vide.",
        )

    # Retire guillemets ou préfixes courants si le modèle en ajoute.
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    if text.lower().startswith("prompt:"):
        text = text.split(":", 1)[1].strip()

    return GeneratePromptResponse(prompt=text)
