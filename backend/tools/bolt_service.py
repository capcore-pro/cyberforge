"""
Service Bolt.new — envoi de prompts et récupération du code généré.

Priorité :
1. API Bolt.new configurée (BOLT_API_KEY + BOLT_API_BASE_URL)
2. Repli OpenAI ou Anthropic (style Bolt, sortie structurée)
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings

BOLT_SYSTEM_PROMPT = """Tu es Bolt.new intégré dans CyberForge.
Génère du code full-stack (React, TypeScript, Tailwind) à partir du prompt utilisateur.
Réponds UNIQUEMENT avec un JSON valide (sans markdown) de la forme :
{
  "summary": "résumé court en français",
  "code": "fichier principal ou extrait principal",
  "files": [{"path": "chemin/relatif", "content": "contenu complet"}],
  "stack": ["react", "typescript", ...]
}
Inclus au moins un fichier dans files. Le champ code doit reprendre le fichier le plus important."""

BOLT_API_GENERATE_PATH = "/v1/generate"


class BoltProvider(str, Enum):
    BOLT_NEW = "bolt.new"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class BoltFile(BaseModel):
    path: str
    content: str


class BoltGenerateResult(BaseModel):
    """Résultat de génération — jamais de secrets."""

    summary: str
    code: str
    files: list[BoltFile] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)
    provider: BoltProvider
    model: str
    project_url: str | None = None


class BoltServiceError(Exception):
    """Erreur métier du service Bolt (configuration ou génération)."""


class BoltService:
    """Client Bolt.new avec repli LLM."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(
            self._has_bolt_api()
            or self._openai_key()
            or self._anthropic_key()
        )

    async def generate(self, prompt: str) -> BoltGenerateResult:
        trimmed = prompt.strip()
        if len(trimmed) < 3:
            raise BoltServiceError("Le prompt doit contenir au moins 3 caractères.")

        if self._has_bolt_api():
            try:
                return await self._call_bolt_api(trimmed)
            except BoltServiceError:
                raise
            except Exception as exc:
                if not (self._openai_key() or self._anthropic_key()):
                    raise BoltServiceError(
                        f"API Bolt.new indisponible : {exc}"
                    ) from exc

        if self._openai_key():
            return await self._generate_openai(trimmed)
        if self._anthropic_key():
            return await self._generate_anthropic(trimmed)

        raise BoltServiceError(
            "Aucune clé configurée. Définissez BOLT_API_KEY + BOLT_API_BASE_URL "
            "ou OPENAI_API_KEY / ANTHROPIC_API_KEY dans .env"
        )

    def _has_bolt_api(self) -> bool:
        key = self._settings.bolt_api_key
        base = self._settings.bolt_api_base_url
        return bool(
            key
            and key.get_secret_value().strip()
            and base
            and base.strip()
        )

    def _openai_key(self) -> str | None:
        key = self._settings.openai_api_key
        if key:
            value = key.get_secret_value().strip()
            return value or None
        return None

    def _anthropic_key(self) -> str | None:
        key = self._settings.anthropic_api_key
        if key:
            value = key.get_secret_value().strip()
            return value or None
        return None

    async def _call_bolt_api(self, prompt: str) -> BoltGenerateResult:
        base = self._settings.bolt_api_base_url or ""
        url = f"{base.rstrip('/')}{BOLT_API_GENERATE_PATH}"
        api_key = self._settings.bolt_api_key
        assert api_key is not None

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json={"prompt": prompt},
            )

        if response.status_code >= 400:
            raise BoltServiceError(
                f"API Bolt.new a répondu {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        return _parse_bolt_api_payload(data)

    async def _generate_openai(self, prompt: str) -> BoltGenerateResult:
        model = self._settings.bolt_model
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._openai_key()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": BOLT_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )

        if response.status_code >= 400:
            raise BoltServiceError(
                f"OpenAI a répondu {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = _parse_llm_json(content)
        return _llm_to_result(parsed, BoltProvider.OPENAI, model)

    async def _generate_anthropic(self, prompt: str) -> BoltGenerateResult:
        model = "claude-3-5-haiku-latest"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._anthropic_key() or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 8192,
                    "system": BOLT_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

        if response.status_code >= 400:
            raise BoltServiceError(
                f"Anthropic a répondu {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        blocks = payload.get("content", [])
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        parsed = _parse_llm_json(text)
        return _llm_to_result(parsed, BoltProvider.ANTHROPIC, model)


def _parse_bolt_api_payload(data: dict[str, Any]) -> BoltGenerateResult:
    """Normalise la réponse de l'API Bolt.new (contrat CyberForge)."""
    files_raw = data.get("files") or []
    files = [
        BoltFile(path=str(f["path"]), content=str(f["content"]))
        for f in files_raw
        if isinstance(f, dict) and "path" in f and "content" in f
    ]
    code = str(data.get("code") or "")
    if not code and files:
        code = files[0].content

    return BoltGenerateResult(
        summary=str(data.get("summary") or "Code généré par Bolt.new"),
        code=code,
        files=files,
        stack=[str(s) for s in data.get("stack") or []],
        provider=BoltProvider.BOLT_NEW,
        model=str(data.get("model") or "bolt.new"),
        project_url=data.get("project_url"),
    )


def _parse_llm_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise BoltServiceError("Réponse LLM non JSON — réessayez.") from exc


def _llm_to_result(
    data: dict[str, Any],
    provider: BoltProvider,
    model: str,
) -> BoltGenerateResult:
    files_raw = data.get("files") or []
    files = [
        BoltFile(path=str(f["path"]), content=str(f["content"]))
        for f in files_raw
        if isinstance(f, dict) and f.get("path") is not None
    ]
    code = str(data.get("code") or "")
    if not code and files:
        code = files[0].content
    if not code:
        raise BoltServiceError("Aucun code généré dans la réponse.")

    stack = data.get("stack") or []
    return BoltGenerateResult(
        summary=str(data.get("summary") or "Code généré (mode Bolt)"),
        code=code,
        files=files,
        stack=[str(s) for s in stack] if isinstance(stack, list) else [],
        provider=provider,
        model=model,
    )
