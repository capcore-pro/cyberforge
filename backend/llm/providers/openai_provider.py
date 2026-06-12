"""Provider OpenAI — API chat/completions via httpx."""

from __future__ import annotations

import httpx

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse
from security.llm_secrets import get_effective_llm_key_for_http


class OpenAIProvider(BaseLLMProvider):
    provider_slug = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_available(self) -> bool:
        from security.llm_secrets import get_effective_llm_key

        return bool(get_effective_llm_key("OPENAI_API_KEY", self._settings))

    async def generate(self, request: LLMRequest) -> LLMResponse:
        api_key = get_effective_llm_key_for_http("OPENAI_API_KEY", self._settings)
        if not api_key:
            raise RuntimeError("OpenAI API key not configured")

        model = (request.model or self.default_model).strip()
        messages: list[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.messages)

        body = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"OpenAI API error {response.status_code}: {response.text[:300]}"
                )
            data = response.json()

        choices = data.get("choices") or []
        content = ""
        if choices:
            content = str((choices[0].get("message") or {}).get("content") or "")
        usage = data.get("usage") or {}
        inp = int(usage.get("prompt_tokens") or 0)
        out = int(usage.get("completion_tokens") or 0)
        return LLMResponse(
            content=content,
            model=str(data.get("model") or model),
            provider=self.provider_slug,
            input_tokens=inp,
            output_tokens=out,
            total_tokens=inp + out,
        )
