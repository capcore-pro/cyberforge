"""Provider Mistral — briefs et analyses via mistral_client."""

from __future__ import annotations

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from llm.mistral_client import mistral_client


class MistralProvider(BaseLLMProvider):
    provider_slug = "mistral"
    default_model = "mistral-small-latest"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        return self._settings.mistral_configured and mistral_client.is_configured()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Mistral API key not configured")

        model = (request.model or self.default_model).strip()
        if "large" in model.lower():
            raw, usage = await mistral_client.complete_large(
                request.messages,
                max_tokens=request.max_tokens,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
            )
        else:
            raw, usage = await mistral_client.complete_small(
                request.messages,
                max_tokens=request.max_tokens,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
            )

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
