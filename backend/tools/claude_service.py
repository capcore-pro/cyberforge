"""
Service Anthropic Claude — génération de code pour CoreMindAI.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"

CODEGEN_SYSTEM_PROMPT = """Tu es CoreMindAI, le moteur de génération de code de CyberForge.
Génère du code full-stack (React, TypeScript, Tailwind) à partir du prompt utilisateur.
Réponds UNIQUEMENT avec un JSON valide (sans markdown) de la forme :
{
  "summary": "résumé court en français",
  "code": "fichier principal ou extrait principal",
  "files": [{"path": "chemin/relatif", "content": "contenu complet"}],
  "stack": ["react", "typescript", ...]
}
Inclus au moins un fichier dans files. Le champ code doit reprendre le fichier le plus important."""


class GeneratedFile(BaseModel):
    path: str
    content: str


class ClaudeCodeResult(BaseModel):
    """Résultat de génération Claude — jamais de secrets."""

    summary: str
    code: str
    files: list[GeneratedFile] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)
    model: str
    provider: str = "anthropic"


class ClaudeServiceError(Exception):
    """Erreur métier du service Claude."""


class ClaudeService:
    """Client Anthropic Messages API pour la génération de code."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def model(self) -> str:
        return self._settings.coremind_claude_model or DEFAULT_CLAUDE_MODEL

    def is_configured(self) -> bool:
        key = self._settings.anthropic_api_key
        return bool(key and key.get_secret_value().strip())

    async def generate_code(self, prompt: str) -> ClaudeCodeResult:
        trimmed = prompt.strip()
        if len(trimmed) < 3:
            raise ClaudeServiceError("Le prompt doit contenir au moins 3 caractères.")

        api_key = self._anthropic_key()
        if not api_key:
            raise ClaudeServiceError(
                "ANTHROPIC_API_KEY non configurée. Ajoutez-la dans .env à la racine du projet."
            )

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 16384,
                    "system": CODEGEN_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": trimmed}],
                },
            )

        if response.status_code >= 400:
            raise ClaudeServiceError(
                f"Anthropic a répondu {response.status_code}: {response.text[:300]}"
            )

        payload = response.json()
        blocks = payload.get("content", [])
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        if not text.strip():
            raise ClaudeServiceError("Réponse Claude vide.")

        parsed = _parse_json_response(text)
        return _to_code_result(parsed, self.model)

    def _anthropic_key(self) -> str | None:
        key = self._settings.anthropic_api_key
        if key:
            value = key.get_secret_value().strip()
            return value or None
        return None


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ClaudeServiceError("Réponse Claude non JSON — réessayez.") from exc


def _to_code_result(data: dict[str, Any], model: str) -> ClaudeCodeResult:
    files_raw = data.get("files") or []
    files = [
        GeneratedFile(path=str(f["path"]), content=str(f["content"]))
        for f in files_raw
        if isinstance(f, dict) and f.get("path") is not None
    ]
    code = str(data.get("code") or "")
    if not code and files:
        code = files[0].content
    if not code:
        raise ClaudeServiceError("Aucun code généré dans la réponse Claude.")

    stack = data.get("stack") or []
    return ClaudeCodeResult(
        summary=str(data.get("summary") or "Code généré par CoreMindAI via Claude"),
        code=code,
        files=files,
        stack=[str(s) for s in stack] if isinstance(stack, list) else [],
        model=model,
    )
