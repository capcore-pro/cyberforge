"""Provider Ollama — API native /api/chat via httpx."""

from __future__ import annotations

import logging

import httpx

from config import Settings, get_settings
from llm.base_provider import BaseLLMProvider, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

_FALLBACK_MODEL = "llama3.2"


class OllamaProvider(BaseLLMProvider):
    provider_slug = "ollama"
    default_model = "qwen3"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _base_url(self) -> str | None:
        raw = (self._settings.ollama_base_url or "").strip()
        if not raw:
            return None
        return raw.rstrip("/")

    def is_available(self) -> bool:
        base = self._base_url()
        if not base:
            return False
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{base}/api/tags")
                return resp.status_code == 200
        except Exception as exc:
            logger.debug("[OllamaProvider] indisponible — %s", exc)
            return False

    async def _list_model_names(self, client: httpx.AsyncClient, base: str) -> set[str]:
        try:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code != 200:
                return set()
            data = resp.json()
            names: set[str] = set()
            for row in data.get("models") or []:
                name = str(row.get("name") or "").strip()
                if name:
                    names.add(name.split(":")[0])
            return names
        except Exception:
            return set()

    async def _resolve_model(
        self,
        client: httpx.AsyncClient,
        base: str,
        requested: str | None,
    ) -> str:
        if requested:
            return requested.strip()
        installed = await self._list_model_names(client, base)
        if self.default_model in installed:
            return self.default_model
        if _FALLBACK_MODEL in installed:
            return _FALLBACK_MODEL
        return self.default_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        base = self._base_url()
        if not base:
            raise RuntimeError("OLLAMA_BASE_URL not configured")

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            role = str(msg.get("role") or "user")
            content = str(msg.get("content") or "")
            messages.append({"role": role, "content": content})

        async with httpx.AsyncClient(timeout=180.0) as client:
            model = await self._resolve_model(client, base, request.model)
            body = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": request.max_tokens,
                    "temperature": request.temperature,
                },
            }
            response = await client.post(f"{base}/api/chat", json=body)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Ollama API error {response.status_code}: {response.text[:300]}"
                )
            data = response.json()

        content = str((data.get("message") or {}).get("content") or "")
        inp = int(data.get("prompt_eval_count") or 0)
        out = int(data.get("eval_count") or 0)
        return LLMResponse(
            content=content,
            model=str(data.get("model") or model),
            provider=self.provider_slug,
            input_tokens=inp,
            output_tokens=out,
            total_tokens=inp + out,
        )
