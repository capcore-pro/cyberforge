"""Routage LLM multi-fournisseurs avec fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from llm.providers.anthropic_provider import AnthropicProvider
from llm.providers.deepseek_provider import DeepSeekProvider
from llm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

ROUTING_RULES: dict[str, dict[str, str]] = {
    "brief": {
        "primary": "anthropic",
        "primary_model": "claude-haiku-4-5-20251001",
        "fallback": "deepseek",
        "fallback_model": "deepseek-chat",
    },
    "generation": {
        "primary": "anthropic",
        "primary_model": "claude-sonnet-4-5",
        "fallback": "openai",
        "fallback_model": "gpt-4o",
    },
    "analysis": {
        "primary": "anthropic",
        "primary_model": "claude-haiku-4-5-20251001",
        "fallback": "deepseek",
        "fallback_model": "deepseek-chat",
    },
    "review": {
        "primary": "anthropic",
        "primary_model": "claude-haiku-4-5-20251001",
        "fallback": "deepseek",
        "fallback_model": "deepseek-chat",
    },
}

_DEFAULT_RULE = ROUTING_RULES["analysis"]


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        all_providers: list[BaseLLMProvider] = [
            AnthropicProvider(self._settings),
            OpenAIProvider(self._settings),
            DeepSeekProvider(self._settings),
        ]
        self._providers: dict[str, BaseLLMProvider] = {
            p.provider_slug: p for p in all_providers if p.is_available()
        }

    def get_available_providers(self) -> list[str]:
        return sorted(self._providers.keys())

    def get_primary_for_task(self, task_type: str) -> str:
        rule = ROUTING_RULES.get(task_type, _DEFAULT_RULE)
        return rule["primary"]

    async def route(
        self,
        request: LLMRequest,
        task_type: str = "analysis",
    ) -> LLMResponse:
        rule = ROUTING_RULES.get(task_type, _DEFAULT_RULE)
        primary_slug = rule["primary"]
        fallback_slug = rule["fallback"]
        primary_error: str | None = None

        primary_provider = self._providers.get(primary_slug)
        if primary_provider:
            try:
                req = LLMRequest(
                    messages=request.messages,
                    system_prompt=request.system_prompt,
                    model=request.model or rule["primary_model"],
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
                return await primary_provider.generate(req)
            except Exception as exc:
                primary_error = str(exc)
                logger.warning(
                    "[LLMRouter] primary %s failed for %s: %s",
                    primary_slug,
                    task_type,
                    exc,
                )

        fallback_provider = self._providers.get(fallback_slug)
        if fallback_provider:
            try:
                req = LLMRequest(
                    messages=request.messages,
                    system_prompt=request.system_prompt,
                    model=request.model or rule["fallback_model"],
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
                response = await fallback_provider.generate(req)
                asyncio.create_task(
                    self._log_fallback(task_type, primary_slug, fallback_slug, primary_error)
                )
                return response
            except Exception as exc:
                msg = (
                    f"LLM routing failed for task '{task_type}': "
                    f"primary={primary_slug} ({primary_error or 'unavailable'}), "
                    f"fallback={fallback_slug} ({exc})"
                )
                raise RuntimeError(msg) from exc

        raise RuntimeError(
            f"Aucun provider LLM disponible pour task '{task_type}' "
            f"(primary={primary_slug}, fallback={fallback_slug})"
        )

    async def _log_fallback(
        self,
        task_type: str,
        primary: str,
        fallback: str,
        primary_error: str | None,
    ) -> None:
        try:
            from db.audit_store import get_audit_store

            await get_audit_store().log(
                event_type="llm_provider_fallback",
                actor_type="system",
                actor_id="llm_router",
                event_data={
                    "task_type": task_type,
                    "primary": primary,
                    "fallback": fallback,
                    "primary_error": primary_error,
                },
            )
        except Exception as exc:
            logger.warning("[LLMRouter] audit fallback ignoré — %s", exc)


llm_router = LLMRouter()


def get_llm_router() -> LLMRouter:
    return llm_router
