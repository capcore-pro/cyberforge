"""Routage LLM multi-fournisseurs avec fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from llm.providers.anthropic_provider import AnthropicProvider
from llm.providers.deepseek_provider import DeepSeekProvider
from llm.providers.gemini_provider import GeminiProvider
from llm.providers.mistral_provider import MistralProvider
from llm.providers.ollama_provider import OllamaProvider
from llm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

ROUTING_RULES: dict[str, dict[str, str]] = {
    "brief": {
        "primary": "mistral",
        "primary_model": "mistral-small-latest",
        "fallback": "gemini",
        "fallback_model": "gemini-2.0-flash",
        "fallback2": "anthropic",
        "fallback2_model": "claude-haiku-4-5-20251001",
        "fallback3": "deepseek",
        "fallback3_model": "deepseek-chat",
        "fallback4": "ollama",
        "fallback4_model": "qwen3",
    },
    "generation": {
        "primary": "anthropic",
        "primary_model": "claude-sonnet-4-5",
        "fallback": "openai",
        "fallback_model": "gpt-4o",
    },
    "analysis": {
        "primary": "mistral",
        "primary_model": "mistral-small-latest",
        "fallback": "gemini",
        "fallback_model": "gemini-2.0-flash",
        "fallback2": "anthropic",
        "fallback2_model": "claude-haiku-4-5-20251001",
        "fallback3": "deepseek",
        "fallback3_model": "deepseek-chat",
        "fallback4": "ollama",
        "fallback4_model": "qwen3",
    },
    "content": {
        "primary": "mistral",
        "primary_model": "mistral-large-latest",
        "fallback": "gemini",
        "fallback_model": "gemini-2.0-flash",
        "fallback2": "anthropic",
        "fallback2_model": "claude-haiku-4-5-20251001",
        "fallback3": "deepseek",
        "fallback3_model": "deepseek-chat",
    },
    "review": {
        "primary": "anthropic",
        "primary_model": "claude-sonnet-4-5",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
    },
}

_DEFAULT_RULE = ROUTING_RULES["analysis"]

_CHAIN_SLOTS: list[tuple[str, str]] = [
    ("primary", "primary_model"),
    ("fallback", "fallback_model"),
    ("fallback2", "fallback2_model"),
    ("fallback3", "fallback3_model"),
    ("fallback4", "fallback4_model"),
]


def _routing_chain(rule: dict[str, str]) -> list[tuple[str, str]]:
    chain: list[tuple[str, str]] = []
    for provider_key, model_key in _CHAIN_SLOTS:
        slug = rule.get(provider_key)
        model = rule.get(model_key)
        if slug and model:
            chain.append((str(slug), str(model)))
    return chain


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._provider_classes: list[type[BaseLLMProvider]] = [
            MistralProvider,
            GeminiProvider,
            AnthropicProvider,
            OpenAIProvider,
            DeepSeekProvider,
            OllamaProvider,
        ]
        self._providers: dict[str, BaseLLMProvider] = {}
        self._refresh_providers()

    def _refresh_providers(self) -> None:
        self._providers = {
            p.provider_slug: p
            for cls in self._provider_classes
            for p in [cls(self._settings)]
            if p.is_available()
        }

    def get_available_providers(self) -> list[str]:
        self._refresh_providers()
        return sorted(self._providers.keys())

    def get_primary_for_task(self, task_type: str) -> str:
        rule = ROUTING_RULES.get(task_type, _DEFAULT_RULE)
        return rule["primary"]

    async def route(
        self,
        request: LLMRequest,
        task_type: str = "analysis",
    ) -> LLMResponse:
        self._refresh_providers()
        rule = ROUTING_RULES.get(task_type, _DEFAULT_RULE)
        chain = _routing_chain(rule)

        errors: list[str] = []
        primary_slug = chain[0][0] if chain else ""

        for index, (slug, model_name) in enumerate(chain):
            provider = self._providers.get(slug)
            if not provider:
                errors.append(f"{slug}=unavailable")
                continue
            try:
                req = LLMRequest(
                    messages=request.messages,
                    system_prompt=request.system_prompt,
                    model=request.model or model_name,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
                response = await provider.generate(req)
                if index > 0:
                    asyncio.create_task(
                        self._log_fallback(
                            task_type,
                            primary_slug,
                            slug,
                            "; ".join(errors) or None,
                        )
                    )
                return response
            except Exception as exc:
                err = f"{slug}={exc}"
                errors.append(err)
                logger.warning(
                    "[LLMRouter] %s failed for %s: %s",
                    slug,
                    task_type,
                    exc,
                )

        raise RuntimeError(
            f"LLM routing failed for task '{task_type}': " + " | ".join(errors)
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
