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
from cost_tracker import maybe_track_cost, usage_from_anthropic_payload, usage_from_openai_payload
from security.llm_secrets import LLM_KEYS_UNAVAILABLE_MSG, get_effective_llm_key

CODEGEN_SYSTEM_PROMPT = """Tu es CoreMindAI (CyberForge). Génère vite un prototype React + TypeScript + Tailwind.
Règles strictes :
- UN seul fichier : src/App.tsx (composant autonome, ≤ 120 lignes, pas de dépendances externes).
- Pas de texte hors JSON, pas de markdown.
- JSON compact uniquement :
{"summary":"1 phrase FR","code":"…contenu App.tsx…","files":[{"path":"src/App.tsx","content":"…"}],"stack":["react","typescript","tailwind"]}
Le champ code = contenu de files[0]. Reste minimal et fonctionnel."""

CODEGEN_DEMO_HTML_PROMPT = """**GÉNÈRE UNIQUEMENT DU HTML/CSS/JS VANILLA PUR. INTERDIT : React, JSX, Tailwind classes, className, useState, import, export, const =>, template literals JSX. OBLIGATOIRE : style CSS inline ou balise style, JS vanilla avec getElementById/addEventListener.**

Tu es CoreMindAI (CyberForge). Génère un livrable DÉMO client en HTML/CSS/JS vanilla autonome.
Règles strictes :
- UN seul fichier : index.html (document complet <!DOCTYPE html>, ≤ 200 lignes).
- PAS de React, JSX, TypeScript, import/export, npm, CDN externes.
- CSS dans <style> dans <head>, interactions simples en <script> vanilla (querySelector, addEventListener).
- UI soignée, responsive (mobile-first), thème sombre cyber (violet/cyan), textes en français.
- Pas de texte hors JSON, pas de markdown.
- JSON compact uniquement :
{"summary":"1 phrase FR","code":"…HTML complet…","files":[{"path":"index.html","content":"<!DOCTYPE html>…"}],"stack":["html","css","javascript"]}
Le champ code = contenu de files[0]."""

DEMO_SEED_SYSTEM_PROMPT = """Tu personnalises les données d'une démo SaaS client. NE GÉNÈRE AUCUN HTML, CSS, JS, React ni JSX.
NE mentionne jamais CyberForge, CapCore ni un nom d'éditeur — uniquement la marque / le métier du client.
Choisis le template le plus adapté au prompt et fournis uniquement des données seed en JSON compact :
{"template":"taskflow","title":"titre page FR","subtitle":"sous-titre FR","brand_name":"nom produit","brand_tag":"tagline courte","user_name":"Prénom Nom","user_role":"rôle métier précis","tasks":[{"text":"tâche FR","completed":false}]}
Templates disponibles (champ template) :
- "taskflow" : gestion de tâches / projets SaaS (tâches collaboratives)
- "landing" : page vitrine (hero, features, CTA — tâches de mise en ligne)
- "crm" : contacts, pipeline (statuts Prospect/Client/Perdu — tâches commerciales)
- "dashboard" : KPIs, graphiques, analytics (tâches de reporting)
- "facturation" : factures (Payée/En attente/En retard — tâches comptables)
- "reservation" : créneaux restaurant (optionnel si réservation explicite)
Règles :
- Utilise le « Type de projet » et la « Demande client » pour le secteur (marketing : noms de campagnes, leads, ROI, CTR, clics ; restaurant : carte, plats, réservations, couverts, chef ; immobilier : mandats, visites, biens).
- Respecte le template indiqué (« Template premium : … » ou « Template imposé ») s'il est présent.
- 3 à 6 tasks ultra-spécifiques au métier (jamais de tâches génériques « reporting Q2 » sans contexte).
- brand_name = nom réel de l'entreprise demandée ; subtitle et user_role alignés sur le métier.
- Pas de markdown, pas de texte hors JSON."""

MAX_USER_PROMPT_CHARS = 2500


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
    demo_seed: dict[str, Any] | None = Field(
        default=None,
        description="Données seed TaskFlow (titre, marque, tâches) pour aperçu et Cloudflare.",
    )


class CodeGenServiceError(Exception):
    """Erreur métier du service de génération."""


@dataclass(frozen=True)
class _ProviderSpec:
    provider_id: str
    model: str
    call: Callable[[str, str, httpx.AsyncClient], Awaitable[str]]


class CodeGenService:
    """Routage DeepSeek → Gemini Flash → Claude Haiku → Claude Sonnet."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._active_system_prompt = CODEGEN_SYSTEM_PROMPT
        self._track_project_id: str | None = None

    def is_configured(self) -> bool:
        return len(self._available_specs(CodeGenComplexity.ELEVEE)) > 0

    def planned_models(self, complexity: CodeGenComplexity) -> list[str]:
        """Liste des modèles configurés qui seront tentés (ordre de coût)."""
        return [
            f"{spec.provider_id} · {spec.model}"
            for spec in self._available_specs(complexity)
        ]

    async def generate_code(
        self,
        prompt: str,
        complexity: CodeGenComplexity = CodeGenComplexity.MOYENNE,
        *,
        demo_html: bool = False,
        project_id: str | None = None,
    ) -> CodeGenerateResult:
        trimmed = prompt.strip()
        if len(trimmed) < 3:
            raise CodeGenServiceError("Le prompt doit contenir au moins 3 caractères.")

        self._active_system_prompt = (
            CODEGEN_DEMO_HTML_PROMPT if demo_html else CODEGEN_SYSTEM_PROMPT
        )

        specs = self._generation_specs(complexity)
        if not specs:
            raise CodeGenServiceError(LLM_KEYS_UNAVAILABLE_MSG)

        prompt_for_llm = _trim_prompt(trimmed)
        timeout = self._http_timeout()
        errors: list[str] = []
        previous_track = self._track_project_id
        self._track_project_id = project_id

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for spec in specs:
                    try:
                        text = await spec.call(prompt_for_llm, spec.model, client)
                        parsed = _parse_json_response(text)
                        return _to_code_result(parsed, spec.provider_id, spec.model)
                    except httpx.TimeoutException:
                        limit = self._settings.coremind_llm_timeout_seconds
                        errors.append(
                            f"{spec.provider_id}/{spec.model}: timeout ({limit:.0f}s)"
                        )
                    except Exception as exc:
                        errors.append(f"{spec.provider_id}/{spec.model}: {exc}")
        finally:
            self._track_project_id = previous_track

        raise CodeGenServiceError(
            "Tous les modèles ont échoué : " + " | ".join(errors[:4])
        )

    async def generate_demo_seed(
        self,
        prompt: str,
        *,
        project_type_label: str = "Démo client",
        template_hint: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Personnalise titre / marque / tâches seed — jamais de HTML."""
        trimmed = prompt.strip()
        if len(trimmed) < 3:
            raise CodeGenServiceError("Le prompt doit contenir au moins 3 caractères.")

        self._active_system_prompt = DEMO_SEED_SYSTEM_PROMPT
        specs = self._available_specs(CodeGenComplexity.FAIBLE)
        if not specs:
            raise CodeGenServiceError(LLM_KEYS_UNAVAILABLE_MSG)

        hint_line = ""
        if template_hint:
            hint_line = f"Template imposé par ArchitectAI : {template_hint.strip()}\n"
        user_msg = (
            f"Type de projet : {project_type_label.strip()}\n"
            f"{hint_line}\n"
            f"Demande client :\n{_trim_prompt(trimmed)}"
        )
        timeout = self._http_timeout()
        errors: list[str] = []
        previous_track = self._track_project_id
        self._track_project_id = project_id

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for spec in specs:
                    try:
                        text = await spec.call(user_msg, spec.model, client)
                        return _parse_json_response(text)
                    except httpx.TimeoutException:
                        limit = self._settings.coremind_llm_timeout_seconds
                        errors.append(
                            f"{spec.provider_id}/{spec.model}: timeout ({limit:.0f}s)"
                        )
                    except Exception as exc:
                        errors.append(f"{spec.provider_id}/{spec.model}: {exc}")
        finally:
            self._track_project_id = previous_track

        raise CodeGenServiceError(
            "Personnalisation seed échouée : " + " | ".join(errors[:4])
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

    def _generation_specs(self, complexity: CodeGenComplexity) -> list[_ProviderSpec]:
        """Fournisseurs à tenter (limités pour respecter le budget temps)."""
        all_specs = self._available_specs(complexity)
        limit = max(1, self._settings.coremind_max_provider_attempts)

        if complexity == CodeGenComplexity.ELEVEE:
            haiku = self._settings.coremind_haiku_model
            sonnet = self._settings.coremind_sonnet_model
            priority = [
                s
                for s in all_specs
                if s.model in (haiku, sonnet)
            ]
            priority.sort(key=lambda s: 0 if s.model == haiku else 1)
            rest = [s for s in all_specs if s not in priority]
            all_specs = priority + rest

        return all_specs[:limit]

    def _http_timeout(self) -> httpx.Timeout:
        seconds = self._settings.coremind_llm_timeout_seconds
        return httpx.Timeout(seconds, connect=min(10.0, seconds))

    def _max_output_tokens(self) -> int:
        return max(256, self._settings.coremind_max_output_tokens)

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

    def _deepseek_key(self) -> str | None:
        return get_effective_llm_key("DEEPSEEK_API_KEY", self._settings)

    def _gemini_key(self) -> str | None:
        return get_effective_llm_key("GOOGLE_GENERATIVE_AI_API_KEY", self._settings)

    def _anthropic_key(self) -> str | None:
        return get_effective_llm_key("ANTHROPIC_API_KEY", self._settings)

    async def _call_deepseek(
        self, prompt: str, model: str, client: httpx.AsyncClient
    ) -> str:
        body, content_headers = _utf8_json_body(
            {
                "model": model,
                "temperature": 0.2,
                "max_tokens": self._max_output_tokens(),
                "messages": [
                    {"role": "system", "content": self._active_system_prompt},
                    {"role": "user", "content": prompt},
                ],
            }
        )
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {self._deepseek_key()}",
                **content_headers,
            },
            content=body,
        )
        text = _extract_openai_text(response, "DeepSeek")
        if self._track_project_id:
            maybe_track_cost(
                self._track_project_id,
                "deepseek_v3",
                usage_from_openai_payload(response.json()),
            )
        return text

    async def _call_gemini(
        self, prompt: str, model: str, client: httpx.AsyncClient
    ) -> str:
        key = self._gemini_key()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={key}"
        )
        body, content_headers = _utf8_json_body(
            {
                "systemInstruction": {"parts": [{"text": self._active_system_prompt}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": self._max_output_tokens(),
                },
            }
        )
        response = await client.post(
            url,
            headers=content_headers,
            content=body,
        )
        if response.status_code >= 400:
            raise CodeGenServiceError(
                f"Gemini a répondu {response.status_code}: "
                f"{_response_text_snippet(response)}"
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

    async def _call_anthropic(
        self, prompt: str, model: str, client: httpx.AsyncClient
    ) -> str:
        body, content_headers = _utf8_json_body(
            {
                "model": model,
                "max_tokens": self._max_output_tokens(),
                "system": self._active_system_prompt,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._anthropic_key() or "",
                "anthropic-version": "2023-06-01",
                **content_headers,
            },
            content=body,
        )
        if response.status_code >= 400:
            raise CodeGenServiceError(
                f"Anthropic a répondu {response.status_code}: "
                f"{_response_text_snippet(response)}"
            )
        payload = response.json()
        blocks = payload.get("content", [])
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        if not text.strip():
            raise CodeGenServiceError("Réponse Anthropic vide.")
        if self._track_project_id and model == self._settings.coremind_sonnet_model:
            maybe_track_cost(
                self._track_project_id,
                "claude_sonnet",
                usage_from_anthropic_payload(payload),
            )
        return text


def _trim_prompt(prompt: str) -> str:
    """Limite la taille du prompt utilisateur pour accélérer la génération."""
    text = prompt.strip()
    if len(text) <= MAX_USER_PROMPT_CHARS:
        return text
    return text[:MAX_USER_PROMPT_CHARS] + "\n… [prompt tronqué]"


def _utf8_json_body(payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    """Sérialise le corps en UTF-8 (évite ascii codec sur Windows avec —, accents, etc.)."""
    return (
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        {"Content-Type": "application/json; charset=utf-8"},
    )


def _response_text_snippet(response: httpx.Response, limit: int = 300) -> str:
    return response.content.decode("utf-8", errors="replace")[:limit]


def _extract_openai_text(response: httpx.Response, label: str) -> str:
    if response.status_code >= 400:
        raise CodeGenServiceError(
            f"{label} a répondu {response.status_code}: "
            f"{_response_text_snippet(response)}"
        )
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if not str(content).strip():
        raise CodeGenServiceError(f"Réponse {label} vide.")
    return str(content)


def _parse_json_response(text: str) -> dict[str, Any]:
    """
    Parse la réponse LLM : JSON strict, JSON embarqué, ou repli code texte libre
    (cas fréquent DeepSeek).
    """
    cleaned = text.strip().lstrip("\ufeff")
    if not cleaned:
        raise CodeGenServiceError("Réponse LLM vide.")

    json_fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
    if json_fence:
        parsed = _try_load_json_object(json_fence.group(1).strip())
        if parsed is not None:
            return parsed

    parsed = _try_load_json_object(cleaned)
    if parsed is not None:
        return parsed

    embedded = _find_embedded_json_object(cleaned)
    if embedded is not None:
        return embedded

    return _fallback_plain_code_payload(cleaned)


def _try_load_json_object(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _find_embedded_json_object(text: str) -> dict[str, Any] | None:
    """Extrait le premier objet JSON équilibré dans un texte mixte."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        quote = ""

        for i in range(start, len(text)):
            char = text[i]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote:
                    in_string = False
            elif char in ('"', "'"):
                in_string = True
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    parsed = _try_load_json_object(text[start : i + 1])
                    if parsed is not None:
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


def _extract_code_fence(text: str) -> str | None:
    match = re.search(r"```(?:\w+)?\s*([\s\S]*?)```", text)
    if not match:
        return None
    body = match.group(1).strip()
    return body or None


def _guess_primary_path(code: str) -> str:
    head = code.lstrip()[:800]
    if head.startswith("<!") or "<html" in head.lower():
        return "index.html"
    if re.search(r"\bdef\s+\w+\s*\(", head):
        return "main.py"
    if (
        re.search(r"\bexport\s+(default\s+)?(function|const)\b", head)
        or "import React" in head
        or ("<" in head and ">" in head and "className" in head)
    ):
        return "src/App.tsx"
    return "src/generated.ts"


def _fallback_plain_code_payload(text: str) -> dict[str, Any]:
    """Repli lorsque le modèle renvoie du code brut sans enveloppe JSON."""
    code = _extract_code_fence(text) or text.strip()
    if not code:
        raise CodeGenServiceError("Réponse LLM non JSON et sans contenu exploitable.")

    path = _guess_primary_path(code)
    summary = "Code généré par CoreMindAI (réponse texte libre du modèle)."
    preamble = text[:200].strip()
    if preamble and preamble != code[:200].strip():
        summary = preamble.split("\n", 1)[0][:240]

    return {
        "summary": summary,
        "code": code,
        "files": [{"path": path, "content": code}],
        "stack": [],
    }


def _to_code_result(
    data: dict[str, Any], provider: str, model: str
) -> CodeGenerateResult:
    from tools.generation_sources import normalize_generation_sources

    files_raw = data.get("files") or []
    initial_files = [
        {"path": str(f["path"]), "content": str(f["content"])}
        for f in files_raw
        if isinstance(f, dict) and f.get("path") is not None
    ]
    initial_code = str(data.get("code") or "") or None
    norm_files, norm_code = normalize_generation_sources(initial_files, initial_code)
    files = [
        GeneratedFile(path=f["path"], content=f["content"]) for f in norm_files
    ]
    code = norm_code or ""
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
