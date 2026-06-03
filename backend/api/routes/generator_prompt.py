"""
Générateur de prompt — aide à la rédaction du brief CyberForge (Anthropic).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from security.llm_secrets import (
    LLM_KEYS_UNAVAILABLE_MSG,
    get_effective_llm_key,
    get_effective_llm_key_for_http,
)
from security.secret_vault import get_secret_vault
from tools.codegen_service import _response_text_snippet, _utf8_json_body

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generator"])

PROMPT_MODEL = "claude-sonnet-4-5"
# Snapshot daté si l'alias n'est pas accepté par le compte API.
PROMPT_MODEL_FALLBACK = "claude-sonnet-4-5-20250929"
MAX_OUTPUT_TOKENS = 1024
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_PROMPT = """Tu es un expert en création de sites web et applications digitales pour PME françaises.
L'utilisateur décrit un projet. Tu dois générer un prompt professionnel ULTRA DÉTAILLÉ
pour CyberForge.

Le prompt doit obligatoirement inclure dans cet ordre :
1. NOM EXACT du projet entre guillemets
2. TYPE précis (site vitrine, e-commerce, application web, etc.)
3. SECTEUR et description de l'activité en 1-2 phrases
4. HÉBERGEMENTS / PRODUITS / SERVICES listés avec détails
5. FONCTIONNALITÉS souhaitées (galerie, contact, réservation, panier, etc.)
6. AMBIANCE VISUELLE précise (moderne, chaleureux, luxe, nature, etc.)
7. PALETTE DE COULEURS avec noms et codes hex si possible
8. TYPOGRAPHIE souhaitée (sobre, élégante, dynamique, etc.)
9. IMAGES souhaitées (fond plein écran forêt, photos produits, équipe, etc.)
10. ÉLÉMENTS SPÉCIAUX (animations, effets hover, parallax, etc.)

RÈGLES ABSOLUES :
- Jamais de markdown, jamais de tirets, jamais de numéros
- Un seul paragraphe fluide et professionnel
- Entre 150 et 250 mots
- Suffisamment précis pour qu'aucune ambiguïté ne soit possible
- Pour une vitrine : ne jamais mentionner réservation en ligne ou booking

Réponds UNIQUEMENT avec le prompt généré, rien d'autre."""

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


def _anthropic_request_body(*, system: str, user_message: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }


def _log_api_key_resolution(settings: Any, http_key: str | None) -> str:
    """Log la provenance de la clé (sans exposer la valeur)."""
    from_vault = bool(get_secret_vault().peek("ANTHROPIC_API_KEY"))
    from_env = bool(get_effective_llm_key("ANTHROPIC_API_KEY", settings))
    source = "vault" if from_vault else ("env" if from_env else "none")
    key_len = len(http_key) if http_key else 0
    logger.info(
        "generate-prompt: clé Anthropic source=%s configured=%s http_key_len=%s",
        source,
        from_vault or from_env,
        key_len,
    )
    return source


def _log_anthropic_error(
    response: httpx.Response,
    *,
    model: str,
    key_source: str,
) -> None:
    request_id = response.headers.get("request-id") or response.headers.get("x-request-id")
    body_text = response.text or ""
    try:
        err_payload = response.json()
        err_block = err_payload.get("error") or err_payload
        err_type = err_block.get("type") if isinstance(err_block, dict) else None
        err_message = err_block.get("message") if isinstance(err_block, dict) else None
    except (json.JSONDecodeError, ValueError):
        err_type = None
        err_message = None

    logger.error(
        "generate-prompt Anthropic HTTP %s model=%s key_source=%s request_id=%s "
        "error_type=%s error_message=%s body=%s",
        response.status_code,
        model,
        key_source,
        request_id,
        err_type,
        err_message,
        body_text[:2000] if body_text else _response_text_snippet(response, limit=2000),
    )


def _model_invalid_response(response: httpx.Response) -> bool:
    text = (response.text or "").lower()
    return response.status_code == 400 and (
        "model" in text or "not_found" in text or "invalid_request" in text
    )


async def _call_anthropic_messages(
    *,
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    system: str,
    user_message: str,
) -> httpx.Response:
    body_payload = _anthropic_request_body(
        system=system,
        user_message=user_message,
        model=model,
    )
    body_bytes, content_headers = _utf8_json_body(body_payload)
    return await client.post(
        ANTHROPIC_MESSAGES_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            **content_headers,
        },
        content=body_bytes,
    )


def _extract_prompt_text(payload: dict[str, Any]) -> str:
    blocks = payload.get("content") or []
    return "".join(
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


def _normalize_generated_prompt(text: str) -> str:
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    if text.lower().startswith("prompt:"):
        text = text.split(":", 1)[1].strip()
    return text


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
    key_source = _log_api_key_resolution(settings, api_key)
    if not api_key:
        logger.warning("generate-prompt: aucune clé Anthropic (coffre verrouillé ou .env vide)")
        raise HTTPException(status_code=503, detail=LLM_KEYS_UNAVAILABLE_MSG)

    idea = body.idea.strip()
    type_label = _KIND_LABELS[kind]
    user_message = (
        f"Type de projet CyberForge : {type_label}.\n\n"
        f"Idée de l'utilisateur :\n{idea}"
    )

    model = PROMPT_MODEL
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            response = await _call_anthropic_messages(
                client=client,
                api_key=api_key,
                model=model,
                system=SYSTEM_PROMPT,
                user_message=user_message,
            )
            if _model_invalid_response(response) and model == PROMPT_MODEL:
                logger.warning(
                    "generate-prompt: retry avec modèle daté %s",
                    PROMPT_MODEL_FALLBACK,
                )
                model = PROMPT_MODEL_FALLBACK
                response = await _call_anthropic_messages(
                    client=client,
                    api_key=api_key,
                    model=model,
                    system=SYSTEM_PROMPT,
                    user_message=user_message,
                )
    except httpx.HTTPError as exc:
        logger.exception("generate-prompt Anthropic HTTP transport error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Impossible de contacter l'API Anthropic.",
        ) from exc

    if response.status_code >= 400:
        _log_anthropic_error(response, model=model, key_source=key_source)
        detail = f"Anthropic a répondu {response.status_code}."
        try:
            err = response.json().get("error") or {}
            if isinstance(err, dict) and err.get("message"):
                detail = f"Anthropic {response.status_code}: {err['message']}"
        except (json.JSONDecodeError, ValueError):
            pass
        raise HTTPException(status_code=502, detail=detail)

    payload = response.json()
    text = _normalize_generated_prompt(_extract_prompt_text(payload))

    if not text:
        logger.error(
            "generate-prompt: réponse Anthropic vide model=%s payload_keys=%s",
            model,
            list(payload.keys()),
        )
        raise HTTPException(
            status_code=502,
            detail="Réponse Anthropic vide.",
        )

    logger.info(
        "generate-prompt OK model=%s request_id=%s chars=%s",
        model,
        response.headers.get("request-id"),
        len(text),
    )
    return GeneratePromptResponse(prompt=text)
