"""Client Google Gemini — couche quasi-gratuite (Flash)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)


def _effective_gemini_api_key() -> str:
    settings = get_settings()
    from security.llm_secrets import get_effective_llm_key

    key = get_effective_llm_key("GOOGLE_GENERATIVE_AI_API_KEY", settings)
    if key:
        return key
    return get_effective_llm_key("GEMINI_API_KEY", settings) or ""


class GeminiClient:
    def __init__(self) -> None:
        self.flash_model = "gemini-2.0-flash"
        self.pro_model = "gemini-2.0-flash"
        self._configured = False
        api_key = _effective_gemini_api_key()
        if api_key:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self._genai = genai
            self._configured = True
        else:
            self._genai = None

    def is_configured(self) -> bool:
        return self._configured

    async def complete(
        self,
        messages: list[dict],
        model: str = "gemini-2.0-flash",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, int]]:
        if not self._configured or self._genai is None:
            raise RuntimeError("Gemini non configuré")

        gemini_model = self._genai.GenerativeModel(model)

        system_parts: list[str] = []
        user_parts: list[str] = []
        if system_prompt:
            system_parts.append(system_prompt.strip())
        for msg in messages:
            role = str(msg.get("role") or "")
            content = str(msg.get("content") or "")
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                user_parts.append(content)
            elif role == "assistant":
                user_parts.append(content)

        if system_parts and user_parts:
            full_prompt = "\n\n".join(system_parts) + "\n\n" + user_parts[-1]
        elif user_parts:
            full_prompt = user_parts[-1]
        else:
            full_prompt = "\n\n".join(system_parts)

        generation_config: dict[str, Any] = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_model.generate_content(
                full_prompt,
                generation_config=generation_config,
            ),
        )
        text = str(getattr(response, "text", "") or "")
        usage_meta = getattr(response, "usage_metadata", None)
        inp = int(getattr(usage_meta, "prompt_token_count", 0) or 0) if usage_meta else 0
        out = int(getattr(usage_meta, "candidates_token_count", 0) or 0) if usage_meta else 0
        return text, {
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": inp + out,
        }

    async def complete_flash(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> tuple[str, dict[str, int]]:
        return await self.complete(
            messages,
            self.flash_model,
            max_tokens,
            temperature,
            system_prompt=system_prompt,
        )


gemini_client = GeminiClient()
