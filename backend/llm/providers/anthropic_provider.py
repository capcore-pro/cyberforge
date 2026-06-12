"""Provider Anthropic — SDK officiel (même pattern que brief_ai)."""

from __future__ import annotations

import asyncio

import anthropic

from agents.llm_usage_utils import usage_from_anthropic_response
from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from security.llm_secrets import get_effective_llm_key


class AnthropicProvider(BaseLLMProvider):
    provider_slug = "anthropic"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.default_model = self._settings.coremind_haiku_model

    def is_available(self) -> bool:
        return bool(get_effective_llm_key("ANTHROPIC_API_KEY", self._settings))

    async def generate(self, request: LLMRequest) -> LLMResponse:
        api_key = get_effective_llm_key("ANTHROPIC_API_KEY", self._settings)
        if not api_key:
            raise RuntimeError("Anthropic API key not configured")

        model = (request.model or self.default_model).strip()
        client = anthropic.Anthropic(api_key=api_key)

        def _call() -> tuple[str, object]:
            kwargs: dict = {
                "model": model,
                "max_tokens": request.max_tokens,
                "messages": request.messages,
            }
            if request.system_prompt:
                kwargs["system"] = request.system_prompt
            response = client.messages.create(**kwargs)
            parts: list[str] = []
            for block in response.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts), response

        raw, response = await asyncio.to_thread(_call)
        usage = usage_from_anthropic_response(response, model) or {}
        inp = int(usage.get("input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        return LLMResponse(
            content=raw,
            model=model,
            provider=self.provider_slug,
            input_tokens=inp,
            output_tokens=out,
            total_tokens=inp + out,
        )
