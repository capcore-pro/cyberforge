"""
Générateurs BuilderAI — v0 (UI React) et DeepSeek (code complexe / backend).
Exécutés sous les ordres de CoreMindAI ; fallback géré par le pipeline.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel

from config import Settings, get_settings, plain_secret_str
from security.llm_secrets import get_effective_llm_key
from tools.codegen_service import (
    CodeGenerateResult,
    GeneratedFile,
    _parse_json_response,
)

logger = logging.getLogger(__name__)

DEFAULT_V0_API_BASE = "https://api.v0.dev/v1"
DEFAULT_V0_MODEL = "v0-1.5-md"

BUILDER_DEEPSEEK_SYSTEM = """Tu es BuilderAI (CyberForge), moteur DeepSeek pour code backend et logique complexe.
Génère un prototype TypeScript/Python ou API selon le brief.
Réponds UNIQUEMENT en JSON compact :
{"summary":"1 phrase FR","code":"…code principal…","files":[{"path":"src/main.ts","content":"…"}],"stack":["typescript","fastapi"]}
Le champ code = contenu du fichier principal."""

BUILDER_V0_SYSTEM = """Tu es v0 intégré à CyberForge. Génère des composants React + Tailwind modernes.
Réponds avec du JSX/TSX dans un bloc de code ou JSON :
{"summary":"1 phrase FR","code":"…tsx…","files":[{"path":"src/App.tsx","content":"…"}],"stack":["react","typescript","tailwind"]}"""


class BuildOutcome(BaseModel):
    """Résultat d'une tentative v0 ou DeepSeek."""

    provider: str
    success: bool
    summary: str = ""
    generation: CodeGenerateResult | None = None
    error: str | None = None


def _code_from_payload(payload: dict[str, Any]) -> tuple[str, list[GeneratedFile]]:
    for key in ("html", "code", "content"):
        raw = payload.get(key)
        if isinstance(raw, str) and len(raw.strip()) > 40:
            text = raw.strip()
            path = "index.html" if key == "html" or text.lstrip().startswith("<!") else "src/App.tsx"
            return text, [GeneratedFile(path=path, content=text)]

    files = payload.get("files")
    if isinstance(files, list) and files:
        parsed: list[GeneratedFile] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "src/App.tsx")
            content = str(item.get("content") or "")
            if content.strip():
                parsed.append(GeneratedFile(path=path, content=content))
        if parsed:
            primary = parsed[0]
            return primary.content, parsed

    raise ValueError("Payload sans code exploitable")


def _code_from_llm_text(text: str, *, default_path: str = "src/App.tsx") -> tuple[str, list[GeneratedFile]]:
    cleaned = text.strip()
    try:
        payload = _parse_json_response(cleaned)
        return _code_from_payload(payload)
    except Exception:
        pass

    fence = re.search(r"```(?:tsx|jsx|typescript|html)?\s*([\s\S]*?)```", cleaned, re.I)
    if fence:
        code = fence.group(1).strip()
        path = "index.html" if code.lstrip().startswith("<!") else default_path
        return code, [GeneratedFile(path=path, content=code)]

    if len(cleaned) > 80:
        return cleaned, [GeneratedFile(path=default_path, content=cleaned)]

    raise ValueError("Réponse sans code exploitable")


def _openai_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("Réponse API vide (choices)")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if not str(content).strip():
        raise ValueError("Réponse API vide (content)")
    return str(content)


class V0Client:
    """Client v0 by Vercel — UI React / Next.js."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def api_key(self) -> str:
        return plain_secret_str(self._settings.v0_api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def base_url(self) -> str:
        return (self._settings.v0_api_base_url or DEFAULT_V0_API_BASE).rstrip("/")

    @property
    def model(self) -> str:
        return self._settings.v0_model or DEFAULT_V0_MODEL

    async def generate_ui(self, prompt: str) -> BuildOutcome:
        if not self.is_configured():
            return BuildOutcome(
                provider="v0",
                success=False,
                error="V0_API_KEY non configurée",
            )

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": BUILDER_V0_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": self._settings.builder_max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        timeout = httpx.Timeout(self._settings.builder_http_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("v0 indisponible : %s", exc)
            return BuildOutcome(provider="v0", success=False, error=str(exc))

        if response.status_code >= 400:
            logger.warning("v0 HTTP %s : %s", response.status_code, response.text[:300])
            return BuildOutcome(
                provider="v0",
                success=False,
                error=f"HTTP {response.status_code}",
            )

        try:
            payload = response.json()
            text = _openai_message_text(payload)
            code, files = _code_from_llm_text(text, default_path="src/App.tsx")
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            return BuildOutcome(provider="v0", success=False, error=str(exc))

        generation = CodeGenerateResult(
            summary="Interface React générée via v0 (Vercel)",
            code=code,
            files=files,
            stack=["react", "typescript", "tailwind"],
            model=self.model,
            provider="v0",
        )
        return BuildOutcome(
            provider="v0",
            success=True,
            summary=generation.summary,
            generation=generation,
        )


class DeepSeekBuilderClient:
    """DeepSeek — génération de code backend / logique complexe."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _api_key(self) -> str:
        key = get_effective_llm_key("DEEPSEEK_API_KEY", self._settings)
        return key or ""

    def is_configured(self) -> bool:
        return bool(self._api_key())

    async def generate_code(self, prompt: str) -> BuildOutcome:
        api_key = self._api_key()
        if not api_key:
            return BuildOutcome(
                provider="deepseek",
                success=False,
                error="DEEPSEEK_API_KEY non configurée",
            )

        model = self._settings.coremind_deepseek_model
        body = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": self._settings.builder_max_output_tokens,
            "messages": [
                {"role": "system", "content": BUILDER_DEEPSEEK_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.builder_http_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    json=body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            logger.warning("DeepSeek Builder indisponible : %s", exc)
            return BuildOutcome(provider="deepseek", success=False, error=str(exc))

        if response.status_code >= 400:
            logger.warning(
                "DeepSeek HTTP %s : %s",
                response.status_code,
                response.text[:300],
            )
            return BuildOutcome(
                provider="deepseek",
                success=False,
                error=f"HTTP {response.status_code}",
            )

        try:
            payload = response.json()
            text = _openai_message_text(payload)
            code, files = _code_from_llm_text(text, default_path="src/main.ts")
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            return BuildOutcome(provider="deepseek", success=False, error=str(exc))

        generation = CodeGenerateResult(
            summary="Code métier généré via DeepSeek (BuilderAI)",
            code=code,
            files=files,
            stack=["typescript", "backend"],
            model=model,
            provider="deepseek",
        )
        return BuildOutcome(
            provider="deepseek",
            success=True,
            summary=generation.summary,
            generation=generation,
        )
