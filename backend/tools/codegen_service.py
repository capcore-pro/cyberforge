"""
Service de génération de code CoreMindAI — routage multi-fournisseurs par coût.

Ordre : DeepSeek → Gemini Flash → Claude Haiku → Claude Sonnet (complexité élevée).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Awaitable

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings

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


class CodeGenComplexity(str, Enum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    ELEVEE = "elevee"


class GeneratedFile(BaseModel):
    path: str
    content: str


class CodeGenerateResult(BaseModel):
    """Résultat de génération — jamais de secrets."""

    summary: str
    code: str
    files: list[GeneratedFile] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)
    model: str
    provider: str


class CodeGenServiceError(Exception):
    """Erreur métier du service de génération."""


@dataclass(frozen=True)
class _ProviderSpec:
    provider_id: str
    model: str
    call: Callable[[str, str], Awaitable[str]]


class CodeGenService:
    """Routage DeepSeek → Gemini Flash → Claude Haiku → Claude Sonnet."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self) -> bool:
        return len(self._available_specs(CodeGenComplexity.ELEVEE)) > 0

    async def generate_code(
        self,
        prompt: str,
        complexity: CodeGenComplexity = CodeGenComplexity.MOYENNE,
    ) -> CodeGenerateResult:
        trimmed = prompt.strip()
        if len(trimmed) < 3:
            raise CodeGenServiceError("Le prompt doit contenir au moins 3 caractères.")

        specs = self._available_specs(complexity)
        if not specs:
            raise CodeGenServiceError(
                "Aucune clé LLM configurée. Ajoutez au moins une clé dans backend/.env : "
                "DEEPSEEK_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY ou ANTHROPIC_API_KEY."
            )

        errors: list[str] = []
        for spec in specs:
            try:
                text = await spec.call(trimmed, spec.model)
                parsed = _parse_json_response(text)
                return _to_code_result(parsed, spec.provider_id, spec.model)
            except Exception as exc:
                errors.append(f"{spec.provider_id}/{spec.model}: {exc}")

        raise CodeGenServiceError(
            "Tous les modèles ont échoué : " + " | ".join(errors[:4])
        )

    def _available_specs(self, complexity: CodeGenComplexity) -> list[_ProviderSpec]:
        chain = self._model_chain(complexity)
        specs: list[_ProviderSpec] = []
        for provider_id, model in chain:
            if provider_id == "deepseek" and self._deepseek_key():
                specs.append(
                    _ProviderSpec("deepseek", model, self._call_deepseek)
                )
            elif provider_id == "gemini" and self._gemini_key():
                specs.append(_ProviderSpec("gemini", model, self._call_gemini))
            elif provider_id.startswith("anthropic") and self._anthropic_key():
                specs.append(
                    _ProviderSpec("anthropic", model, self._call_anthropic)
                )
        return specs

    def _model_chain(
        self, complexity: CodeGenComplexity
    ) -> list[tuple[str, str]]:
        """Ordre de coût croissant ; Sonnet uniquement si complexité élevée."""
        s = self._settings
        chain: list[tuple[str, str]] = [
            ("deepseek", s.coremind_deepseek_model),
            ("gemini", s.coremind_gemini_model),
            ("anthropic", s.coremind_haiku_model),
        ]
        if complexity == CodeGenComplexity.ELEVEE:
            chain.append(("anthropic", s.coremind_sonnet_model))
        return chain

    def _secret(self, value: Any) -> str | None:
        if value is None:
            return None
        text = value.get_secret_value().strip()
        return text or None

    def _deepseek_key(self) -> str | None:
        return self._secret(self._settings.deepseek_api_key)

    def _gemini_key(self) -> str | None:
        return self._secret(self._settings.google_generative_ai_api_key)

    def _anthropic_key(self) -> str | None:
        return self._secret(self._settings.anthropic_api_key)

    async def _call_deepseek(self, prompt: str, model: str) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._deepseek_key()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": CODEGEN_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        return _extract_openai_text(response, "DeepSeek")

    async def _call_gemini(self, prompt: str, model: str) -> str:
        key = self._gemini_key()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={key}"
        )
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": CODEGEN_SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2},
                },
            )
        if response.status_code >= 400:
            raise CodeGenServiceError(
                f"Gemini a répondu {response.status_code}: {response.text[:300]}"
            )
        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise CodeGenServiceError("Réponse Gemini vide.")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        if not text.strip():
            raise CodeGenServiceError("Réponse Gemini vide.")
        return text

    async def _call_anthropic(self, prompt: str, model: str) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._anthropic_key() or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 16384,
                    "system": CODEGEN_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if response.status_code >= 400:
            raise CodeGenServiceError(
                f"Anthropic a répondu {response.status_code}: {response.text[:300]}"
            )
        payload = response.json()
        blocks = payload.get("content", [])
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        if not text.strip():
            raise CodeGenServiceError("Réponse Anthropic vide.")
        return text


def _extract_openai_text(response: httpx.Response, label: str) -> str:
    if response.status_code >= 400:
        raise CodeGenServiceError(
            f"{label} a répondu {response.status_code}: {response.text[:300]}"
        )
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if not str(content).strip():
        raise CodeGenServiceError(f"Réponse {label} vide.")
    return str(content)


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CodeGenServiceError("Réponse LLM non JSON — réessayez.") from exc


def _to_code_result(
    data: dict[str, Any], provider: str, model: str
) -> CodeGenerateResult:
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
        raise CodeGenServiceError("Aucun code généré dans la réponse.")

    stack = data.get("stack") or []
    return CodeGenerateResult(
        summary=str(data.get("summary") or "Code généré par CoreMindAI"),
        code=code,
        files=files,
        stack=[str(s) for s in stack] if isinstance(stack, list) else [],
        model=model,
        provider=provider,
    )


def complexity_from_score(score: int) -> CodeGenComplexity:
    if score <= 3:
        return CodeGenComplexity.FAIBLE
    if score <= 6:
        return CodeGenComplexity.MOYENNE
    return CodeGenComplexity.ELEVEE
