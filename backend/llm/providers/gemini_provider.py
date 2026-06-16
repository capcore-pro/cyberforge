"""Provider Google Gemini — Flash quasi-gratuit via gemini_client."""

from __future__ import annotations

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from llm.gemini_client import gemini_client


class GeminiProvider(BaseLLMProvider):
    provider_slug = "gemini"
    default_model = "gemini-2.0-flash"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        return self._settings.gemini_configured and gemini_client.is_configured()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")

        model = (request.model or self.default_model).strip()
        raw, usage = await gemini_client.complete_flash(
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
